"""
Smart Resolver — deterministic entity resolution for Impact Radar.
No LLM for matching. SQL + pg_trgm + aliases + graph evidence + optional embeddings.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.resolver import AutocompleteSuggestion, SmartResolvedEntity

logger = logging.getLogger(__name__)

TRGM_THRESHOLD = 0.35
EMBEDDING_DIM = 128

STOP_WORDS = frozenset(
    """
    a an the what if i change modify remove delete update fix break happens
    depends on which features use can safely will would should my this that
    when where how why who is are was were be been being have has had do does
    did doing would could should may might must shall
    """.split()
)

QUERY_EXPANSIONS: dict[str, list[str]] = {
    "login": ["github", "oauth", "auth", "callback", "session", "sign"],
    "oauth": ["github", "auth", "callback", "token"],
    "github": ["oauth", "auth", "connect", "callback"],
    "authentication": ["auth", "oauth", "login"],
    "repository": ["repo", "connect", "analyze"],
    "analysis": ["analyze", "parser", "scan"],
    "session": ["token", "auth", "cookie"],
    "connect": ["repo", "github", "repository"],
}


@dataclass
class ResolverCandidate:
    entity_id: str
    entity_type: str
    name: str
    file_path: str = ""
    http_method: str | None = None
    route_path: str | None = None
    points: int = 0
    sources: list[str] = field(default_factory=list)
    matched_alias: str | None = None
    workflow_name: str | None = None
    graph_connections: list[str] = field(default_factory=list)

    def add_points(self, pts: int, source: str) -> None:
        self.points += pts
        if source not in self.sources:
            self.sources.append(source)


def tokenize_query(query: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z0-9_./-]+", query.lower())
    tokens = [t for t in raw if len(t) > 1 and t not in STOP_WORDS]
    seen: set[str] = set()
    expanded: list[str] = []
    for t in tokens:
        if t not in seen:
            expanded.append(t)
            seen.add(t)
        for extra in QUERY_EXPANSIONS.get(t, []):
            if extra not in seen:
                expanded.append(extra)
                seen.add(extra)
    return expanded[:16]


def build_deterministic_embedding(text: str) -> list[float]:
    """Hash-based bag-of-words vector — deterministic, no external API."""
    vec = [0.0] * EMBEDDING_DIM
    words = re.findall(r"[a-z0-9]+", text.lower())
    if not words:
        return vec
    for word in words:
        h = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = h % EMBEDDING_DIM
        vec[idx] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def _uuid_str(val) -> str:
    return str(val) if isinstance(val, UUID) else val


class SmartResolver:
    def __init__(self) -> None:
        self._candidates: dict[str, ResolverCandidate] = {}

    async def _rollback_session(self, db: AsyncSession, exc: Exception, *, step: str) -> None:
        """Reset aborted PostgreSQL transactions after optional resolver steps fail."""
        logger.debug("Resolver step %s skipped (%s), rolling back", step, exc)
        try:
            await db.rollback()
        except Exception as rb_exc:
            logger.warning("Resolver rollback failed after %s: %s", step, rb_exc)

    async def resolve(
        self,
        query: str,
        repo_id: str,
        db: AsyncSession,
        *,
        user_id: str | None = None,
        limit: int = 10,
    ) -> tuple[list[SmartResolvedEntity], int, dict | None]:
        start = time.time()
        self._candidates = {}
        q = query.strip()
        if not q:
            return [], 0, None

        tokens = tokenize_query(q)
        search_phrase = " ".join(tokens) if tokens else q.lower()

        exact = await self.exact_match(q, repo_id, db)
        if exact:
            ranked = await self._finalize(exact, repo_id, db, limit)
            primary = await self.resolve_primary_source_node(ranked, repo_id, db)
            ms = int((time.time() - start) * 1000)
            await self._log(repo_id, user_id, q, ranked, ms, db)
            return ranked, ms, primary

        await self.alias_search(q, search_phrase, repo_id, db)
        await self.node_search(q, search_phrase, tokens, repo_id, db)
        await self.file_search(q, search_phrase, tokens, repo_id, db)
        await self.api_search(q, search_phrase, tokens, repo_id, db)
        await self.workflow_search(q, search_phrase, repo_id, db)
        await self.fuzzy_search(q, search_phrase, repo_id, db)
        await self.semantic_search(q, search_phrase, repo_id, db)

        await self.graph_expansion(repo_id, db)

        ranked = self.rank_candidates(limit)
        ranked = await self._enrich_reasoning(ranked, q, repo_id, db)
        primary = await self.resolve_primary_source_node(ranked, repo_id, db)
        ms = int((time.time() - start) * 1000)
        await self._log(repo_id, user_id, q, ranked, ms, db)
        return ranked, ms, primary

    async def exact_match(
        self, query: str, repo_id: str, db: AsyncSession
    ) -> list[SmartResolvedEntity] | None:
        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, n.full_path) as file_path,
                   n.http_method, n.route_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
              AND LOWER(n.name) = LOWER(:query)
            LIMIT 1
        """)
        row = (await db.execute(sql, {"repo_id": repo_id, "query": query})).mappings().first()
        if row:
            c = self._upsert_node(row)
            c.add_points(100, "exact")
            return [self._to_entity(c, 100)]

        path_sql = text("""
            SELECT n.id, n.name, n.node_type,
                   rf.file_path, n.http_method, n.route_path
            FROM nodes n
            JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
              AND rf.file_path ILIKE :pattern
            LIMIT 1
        """)
        row = (
            await db.execute(
                path_sql,
                {"repo_id": repo_id, "pattern": f"%{query}%"},
            )
        ).mappings().first()
        if row:
            c = self._upsert_node(row)
            c.add_points(100, "exact_file")
            return [self._to_entity(c, 100)]
        return None

    async def alias_search(
        self, query: str, phrase: str, repo_id: str, db: AsyncSession
    ) -> None:
        sql = text("""
            SELECT a.alias, a.entity_type, a.weight, a.node_id, a.file_id,
                   n.name, n.node_type, n.http_method, n.route_path,
                   COALESCE(rf.file_path, n.full_path, '') as file_path
            FROM aliases a
            LEFT JOIN nodes n ON a.node_id = n.id
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE a.repo_id = :repo_id
              AND (
                LOWER(a.alias) = LOWER(:query)
                OR a.alias ILIKE :pattern
                OR similarity(LOWER(a.alias), LOWER(:phrase)) > :threshold
              )
            ORDER BY similarity(LOWER(a.alias), LOWER(:phrase)) DESC NULLS LAST
            LIMIT 20
        """)
        try:
            rows = (
                await db.execute(
                    sql,
                    {
                        "repo_id": repo_id,
                        "query": query,
                        "pattern": f"%{phrase}%",
                        "phrase": phrase[:200],
                        "threshold": TRGM_THRESHOLD,
                    },
                )
            ).mappings()
        except (DBAPIError, Exception) as exc:
            await self._rollback_session(db, exc, step="alias_search_trgm")
            try:
                rows = (
                    await db.execute(
                        text("""
                            SELECT a.alias, a.entity_type, a.weight, a.node_id, a.file_id,
                                   n.name, n.node_type, n.http_method, n.route_path,
                                   COALESCE(rf.file_path, '') as file_path
                            FROM aliases a
                            LEFT JOIN nodes n ON a.node_id = n.id
                            LEFT JOIN repo_files rf ON n.file_id = rf.id
                            WHERE a.repo_id = :repo_id
                              AND (LOWER(a.alias) = LOWER(:query) OR a.alias ILIKE :pattern)
                            LIMIT 20
                        """),
                        {"repo_id": repo_id, "query": query, "pattern": f"%{phrase}%"},
                    )
                ).mappings()
            except (DBAPIError, Exception) as fallback_exc:
                await self._rollback_session(db, fallback_exc, step="alias_search")
                return

        for row in rows:
            if row["node_id"]:
                c = self._upsert_node(row, name=row["name"] or row["alias"])
                c.matched_alias = row["alias"]
                c.add_points(25, "alias")
                if row["entity_type"] == "workflow_link":
                    c.workflow_name = row["alias"]
                    c.add_points(15, "workflow")
            elif row["entity_type"] == "workflow":
                key = f"workflow:{row['alias']}"
                if key not in self._candidates:
                    self._candidates[key] = ResolverCandidate(
                        entity_id=key,
                        entity_type="workflow",
                        name=row["alias"],
                    )
                self._candidates[key].matched_alias = row["alias"]
                self._candidates[key].workflow_name = row["alias"]
                self._candidates[key].add_points(25, "alias")
                self._candidates[key].add_points(15, "workflow")

    async def node_search(
        self,
        query: str,
        phrase: str,
        tokens: list[str],
        repo_id: str,
        db: AsyncSession,
    ) -> None:
        patterns = [f"%{t}%" for t in tokens[:8]] or [f"%{phrase}%"]
        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, n.full_path) as file_path,
                   n.http_method, n.route_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
              AND (
                n.name ILIKE ANY(:patterns)
                OR n.full_path ILIKE ANY(:patterns)
                OR n.summary ILIKE ANY(:patterns)
              )
            LIMIT 25
        """)
        for row in (await db.execute(sql, {"repo_id": repo_id, "patterns": patterns})).mappings():
            c = self._upsert_node(row)
            c.add_points(10, "node")

    async def file_search(
        self,
        query: str,
        phrase: str,
        tokens: list[str],
        repo_id: str,
        db: AsyncSession,
    ) -> None:
        pattern = f"%{phrase}%"
        sql = text("""
            SELECT n.id, n.name, n.node_type, rf.file_path,
                   n.http_method, n.route_path
            FROM repo_files rf
            JOIN nodes n ON n.file_id = rf.id AND n.repo_id = rf.repo_id
            WHERE rf.repo_id = :repo_id AND rf.file_path ILIKE :pattern
            LIMIT 15
        """)
        for row in (await db.execute(sql, {"repo_id": repo_id, "pattern": pattern})).mappings():
            c = self._upsert_node(row)
            c.add_points(10, "file")

    async def api_search(
        self,
        query: str,
        phrase: str,
        tokens: list[str],
        repo_id: str,
        db: AsyncSession,
    ) -> None:
        pattern = f"%{phrase}%"
        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, '') as file_path,
                   n.http_method, n.route_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
              AND n.node_type = 'api_route'
              AND (
                n.route_path ILIKE :pattern
                OR n.name ILIKE :pattern
                OR COALESCE(n.http_method, '') ILIKE :pattern
              )
            LIMIT 15
        """)
        for row in (await db.execute(sql, {"repo_id": repo_id, "pattern": pattern})).mappings():
            c = self._upsert_node(row)
            c.add_points(15, "api")

    async def workflow_search(
        self, query: str, phrase: str, repo_id: str, db: AsyncSession
    ) -> None:
        pattern = f"%{phrase}%"
        sql = text("""
            SELECT alias as name, entity_type
            FROM aliases
            WHERE repo_id = :repo_id
              AND entity_type IN ('workflow', 'workflow_link')
              AND alias ILIKE :pattern
            LIMIT 10
        """)
        try:
            result = await db.execute(sql, {"repo_id": repo_id, "pattern": pattern})
        except (DBAPIError, Exception) as e:
            await self._rollback_session(db, e, step="workflow_search")
            return
        for row in result.mappings():
            key = f"workflow:{row['name']}"
            if key not in self._candidates:
                self._candidates[key] = ResolverCandidate(
                    entity_id=key,
                    entity_type="workflow",
                    name=row["name"],
                    workflow_name=row["name"],
                )
            self._candidates[key].add_points(15, "workflow")

    async def fuzzy_search(self, query: str, phrase: str, repo_id: str, db: AsyncSession) -> None:
        sql = text("""
            SELECT n.id, n.name, n.node_type,
                   COALESCE(rf.file_path, n.full_path) as file_path,
                   n.http_method, n.route_path,
                   similarity(LOWER(n.name), LOWER(:phrase)) as sim
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
              AND similarity(LOWER(n.name), LOWER(:phrase)) > :threshold
            ORDER BY sim DESC
            LIMIT 20
        """)
        try:
            rows = (
                await db.execute(
                    sql,
                    {
                        "repo_id": repo_id,
                        "phrase": phrase[:200],
                        "threshold": TRGM_THRESHOLD,
                    },
                )
            ).mappings()
            for row in rows:
                c = self._upsert_node(row)
                c.add_points(15, "trgm_fuzzy")
        except (DBAPIError, Exception) as e:
            await self._rollback_session(db, e, step="fuzzy_search")

    async def semantic_search(self, query: str, phrase: str, repo_id: str, db: AsyncSession) -> None:
        query_emb = build_deterministic_embedding(phrase)
        sql = text("""
            SELECT ne.node_id, ne.embedding, n.name, n.node_type,
                   COALESCE(rf.file_path, n.full_path) as file_path,
                   n.http_method, n.route_path
            FROM node_embeddings ne
            JOIN nodes n ON n.id = ne.node_id
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE ne.repo_id = :repo_id
            LIMIT 500
        """)
        try:
            rows = (await db.execute(sql, {"repo_id": repo_id})).mappings()
        except (DBAPIError, Exception) as e:
            await self._rollback_session(db, e, step="semantic_search")
            return

        scored: list[tuple[float, dict]] = []
        for row in rows:
            emb = row["embedding"]
            if isinstance(emb, str):
                import json

                emb = json.loads(emb)
            if not isinstance(emb, list):
                continue
            sim = cosine_similarity(query_emb, emb)
            if sim > 0.25:
                scored.append((sim, dict(row)))

        scored.sort(key=lambda x: x[0], reverse=True)
        for sim, row in scored[:15]:
            c = self._upsert_node(row)
            pts = int(20 * min(1.0, sim / 0.5))
            c.add_points(max(pts, 8), "semantic_embedding")

    async def graph_expansion(self, repo_id: str, db: AsyncSession) -> None:
        node_ids = [
            c.entity_id
            for c in self._candidates.values()
            if c.entity_type not in ("workflow",) and not c.entity_id.startswith("workflow:")
        ][:8]
        if not node_ids:
            return

        uuid_ids: list[UUID] = []
        for nid in node_ids:
            try:
                uuid_ids.append(UUID(nid))
            except ValueError:
                continue
        if not uuid_ids:
            return

        sql = text("""
            SELECT e.from_node_id, e.to_node_id, n.name
            FROM edges e
            JOIN nodes n ON (
                (n.id = e.to_node_id AND e.from_node_id = ANY(:ids))
                OR (n.id = e.from_node_id AND e.to_node_id = ANY(:ids))
            )
            WHERE e.repo_id = :repo_id
            LIMIT 40
        """)
        try:
            rows = (
                await db.execute(sql, {"repo_id": repo_id, "ids": uuid_ids})
            ).mappings()
        except (DBAPIError, Exception) as e:
            await self._rollback_session(db, e, step="graph_expansion")
            return

        neighbor_names: dict[str, list[str]] = {nid: [] for nid in node_ids}

        for row in rows:
            fid, tid = _uuid_str(row["from_node_id"]), _uuid_str(row["to_node_id"])
            if fid in neighbor_names and tid not in node_ids:
                neighbor_names[fid].append(row["name"])
            if tid in neighbor_names and fid not in node_ids:
                neighbor_names[tid].append(row["name"])

        for nid, names in neighbor_names.items():
            if nid in self._candidates and names:
                self._candidates[nid].graph_connections = list(dict.fromkeys(names))[:6]
                self._candidates[nid].add_points(20, "graph")

    def rank_candidates(self, limit: int) -> list[SmartResolvedEntity]:
        items = list(self._candidates.values())
        for c in items:
            c.points = min(100, c.points)
        items.sort(key=lambda x: x.points, reverse=True)
        return [self._to_entity(c, self.calculate_confidence(c)) for c in items[:limit]]

    def calculate_confidence(self, c: ResolverCandidate) -> int:
        return min(100, max(0, c.points))

    async def _enrich_reasoning(
        self,
        entities: list[SmartResolvedEntity],
        query: str,
        repo_id: str,
        db: AsyncSession,
    ) -> list[SmartResolvedEntity]:
        for ent in entities:
            ent.reason = self.generate_reasoning(ent, query)
        return entities

    async def resolve_primary_source_node(
        self,
        entities: list[SmartResolvedEntity],
        repo_id: str,
        db: AsyncSession,
    ) -> dict | None:
        """Pick best graph node for impact traversal (skip workflow-only hits)."""
        for ent in entities:
            if ent.entity_type == "workflow" or ent.entity_id.startswith("workflow:"):
                continue
            try:
                UUID(ent.entity_id)
            except ValueError:
                continue
            row = (
                await db.execute(
                    text("""
                        SELECT n.id, n.name, n.node_type,
                               COALESCE(rf.file_path, n.full_path) as file_path,
                               n.start_line, n.end_line,
                               n.http_method, n.route_path, n.summary
                        FROM nodes n
                        LEFT JOIN repo_files rf ON n.file_id = rf.id
                        WHERE n.id = :id AND n.repo_id = :repo_id
                    """),
                    {"id": ent.entity_id, "repo_id": repo_id},
                )
            ).mappings().first()
            if row:
                return {
                    "id": _uuid_str(row["id"]),
                    "name": row["name"],
                    "node_type": row["node_type"],
                    "file_path": row["file_path"] or "",
                    "start_line": row["start_line"],
                    "end_line": row["end_line"],
                    "http_method": row["http_method"],
                    "route_path": row["route_path"],
                    "summary": row["summary"],
                }
        return None

    def generate_reasoning(self, ent: SmartResolvedEntity, query: str) -> str:
        parts = []
        if "exact" in ent.source:
            return f'Exact match for "{query}" in repository graph.'
        if ent.reason:
            parts.append(ent.reason)
        elif "alias" in ent.source:
            parts.append(f'Matched alias for "{query}".')
        if ent.workflow_name:
            parts.append(f"Associated workflow: {ent.workflow_name}.")
        if ent.route_path:
            parts.append(f"API: {ent.http_method or 'GET'} {ent.route_path}.")
        if ent.graph_connections:
            parts.append(f"Graph connections: {', '.join(ent.graph_connections[:5])}.")
        if not parts:
            parts.append(f"Matched repository entity via {ent.source}.")
        return " ".join(parts)

    async def autocomplete(
        self,
        query: str,
        repo_id: str,
        db: AsyncSession,
        limit: int = 12,
    ) -> list[AutocompleteSuggestion]:
        if not query or len(query.strip()) < 1:
            return await self._popular_suggestions(repo_id, db, limit)

        q = query.strip()
        pattern = f"%{q}%"
        suggestions: list[AutocompleteSuggestion] = []
        seen: set[str] = set()

        def add(label: str, entity_type: str, source: str, **kwargs) -> None:
            key = f"{entity_type}:{label.lower()}"
            if key in seen:
                return
            seen.add(key)
            suggestions.append(
                AutocompleteSuggestion(
                    label=label,
                    entity_type=entity_type,
                    source=source,
                    **kwargs,
                )
            )

        alias_sql = text("""
            SELECT DISTINCT a.alias, a.entity_type, a.node_id,
                   COALESCE(n.name, a.alias) as name,
                   COALESCE(rf.file_path, '') as file_path
            FROM aliases a
            LEFT JOIN nodes n ON a.node_id = n.id
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE a.repo_id = :repo_id AND a.alias ILIKE :pattern
            ORDER BY a.alias
            LIMIT 8
        """)
        for row in (await db.execute(alias_sql, {"repo_id": repo_id, "pattern": pattern})).mappings():
            add(
                row["alias"],
                row["entity_type"],
                "alias",
                entity_id=_uuid_str(row["node_id"]) if row["node_id"] else None,
                file_path=row["file_path"] or None,
                subtitle=row["name"] if row["name"] != row["alias"] else None,
            )

        node_sql = text("""
            SELECT n.id, n.name, n.node_type, COALESCE(rf.file_path, '') as file_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id
              AND (n.name ILIKE :pattern OR rf.file_path ILIKE :pattern)
            ORDER BY n.name
            LIMIT 8
        """)
        for row in (await db.execute(node_sql, {"repo_id": repo_id, "pattern": pattern})).mappings():
            add(
                row["name"],
                row["node_type"],
                "node",
                entity_id=_uuid_str(row["id"]),
                file_path=row["file_path"] or None,
            )

        api_sql = text("""
            SELECT n.id, n.name, n.http_method, n.route_path,
                   COALESCE(rf.file_path, '') as file_path
            FROM nodes n
            LEFT JOIN repo_files rf ON n.file_id = rf.id
            WHERE n.repo_id = :repo_id AND n.node_type = 'api_route'
              AND (n.route_path ILIKE :pattern OR n.name ILIKE :pattern)
            LIMIT 5
        """)
        for row in (await db.execute(api_sql, {"repo_id": repo_id, "pattern": pattern})).mappings():
            label = f"{row.get('http_method') or 'GET'} {row.get('route_path') or row['name']}"
            add(label.strip(), "api_route", "api", entity_id=_uuid_str(row["id"]), file_path=row["file_path"])

        return suggestions[:limit]

    async def _popular_suggestions(
        self, repo_id: str, db: AsyncSession, limit: int
    ) -> list[AutocompleteSuggestion]:
        from app.services.alias_seeder import POPULAR_SEARCHES

        sql = text("""
            SELECT alias, entity_type, node_id
            FROM aliases
            WHERE repo_id = :repo_id
            GROUP BY alias, entity_type, node_id
            ORDER BY MAX(weight) DESC, alias
            LIMIT :limit
        """)
        rows = (
            await db.execute(sql, {"repo_id": repo_id, "limit": limit})
        ).mappings().all()

        out: list[AutocompleteSuggestion] = []
        for row in rows:
            out.append(
                AutocompleteSuggestion(
                    label=row["alias"],
                    entity_type=row["entity_type"],
                    entity_id=_uuid_str(row["node_id"]) if row["node_id"] else None,
                    source="popular",
                )
            )
        if len(out) < limit:
            for p in POPULAR_SEARCHES:
                if len(out) >= limit:
                    break
                if not any(s.label == p for s in out):
                    out.append(
                        AutocompleteSuggestion(
                            label=p, entity_type="hint", source="popular"
                        )
                    )
        return out

    def _row_node_id(self, row) -> str:
        if row.get("id") is not None:
            return _uuid_str(row["id"])
        if row.get("node_id") is not None:
            return _uuid_str(row["node_id"])
        raise KeyError("row missing id and node_id")

    def _upsert_node(self, row, name: str | None = None) -> ResolverCandidate:
        nid = self._row_node_id(row)
        if nid not in self._candidates:
            self._candidates[nid] = ResolverCandidate(
                entity_id=nid,
                entity_type=row.get("node_type") or "function",
                name=name or row["name"],
                file_path=row.get("file_path") or "",
                http_method=row.get("http_method"),
                route_path=row.get("route_path"),
            )
        return self._candidates[nid]

    def _to_entity(self, c: ResolverCandidate, confidence: int) -> SmartResolvedEntity:
        source = "+".join(c.sources) if c.sources else "unknown"
        reason = ""
        if c.matched_alias:
            reason = f'Matched alias "{c.matched_alias}"'
        return SmartResolvedEntity(
            entity_id=c.entity_id,
            entity_type=c.entity_type,
            name=c.name,
            confidence=confidence,
            reason=reason,
            source=source,
            file_path=c.file_path or None,
            http_method=c.http_method,
            route_path=c.route_path,
            workflow_name=c.workflow_name,
            graph_connections=c.graph_connections,
        )

    async def _finalize(
        self,
        entities: list[SmartResolvedEntity],
        repo_id: str,
        db: AsyncSession,
        limit: int,
    ) -> list[SmartResolvedEntity]:
        if entities and entities[0].entity_type not in ("workflow",):
            nid = entities[0].entity_id
            if not nid.startswith("workflow:"):
                c = self._candidates.get(nid) or ResolverCandidate(
                    entity_id=nid,
                    entity_type=entities[0].entity_type,
                    name=entities[0].name,
                )
                self._candidates[nid] = c
                await self.graph_expansion(repo_id, db)
                entities[0].graph_connections = c.graph_connections
                entities[0].reason = self.generate_reasoning(entities[0], "")
        return entities[:limit]

    async def _log(
        self,
        repo_id: str,
        user_id: str | None,
        query: str,
        ranked: list[SmartResolvedEntity],
        ms: int,
        db: AsyncSession,
    ) -> None:
        try:
            top = ranked[0] if ranked else None
            import json

            await db.execute(
                text("""
                    INSERT INTO resolver_logs (
                        repo_id, user_id, query, top_entity_id, top_entity_name,
                        top_confidence, candidate_count, resolution_ms, candidates_json
                    ) VALUES (
                        :repo_id, :user_id, :query, :top_id, :top_name,
                        :top_conf, :count, :ms, CAST(:candidates AS jsonb)
                    )
                """),
                {
                    "repo_id": repo_id,
                    "user_id": user_id,
                    "query": query,
                    "top_id": top.entity_id if top and not top.entity_id.startswith("workflow:") else None,
                    "top_name": top.name if top else None,
                    "top_conf": top.confidence if top else None,
                    "count": len(ranked),
                    "ms": ms,
                    "candidates": json.dumps(
                        [e.model_dump(mode="json") for e in ranked[:10]]
                    ),
                },
            )
        except (DBAPIError, Exception) as e:
            await self._rollback_session(db, e, step="resolver_log")
