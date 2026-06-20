import asyncio
import json
import logging
import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.architecture import ArchitectureStory, StoryChapter
from app.services.architecture_health import ArchitectureHealthService
from app.services.architecture_service import ArchitectureService
from app.services.flow_reconstruction_service import FlowReconstructionService
from app.utils.groq_client import groq_client

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS = 3000
GROQ_TEMPERATURE = 0.2

class ArchitectureStoryService:
    @staticmethod
    async def generate_story(repo_id: UUID, db: AsyncSession) -> ArchitectureStory:
        # Gather Data
        health_svc = ArchitectureHealthService()
        arch_svc = ArchitectureService()
        flow_svc = FlowReconstructionService()

        # 1. Health report
        health = await health_svc.evaluate_health(repo_id, db)
        
        # 2. Architecture overview & components
        overview = await arch_svc.get_overview(repo_id, db)
        components = await arch_svc.get_components(repo_id, db)
        
        # 3. Flow summaries
        flows, _ = await flow_svc.list_flows(repo_id, db)
        
        # Pack evidence for the LLM
        evidence = {
            "health_score": health.overall_score,
            "architecture_health": health.architecture_health,
            "hotspots": [h.model_dump() for h in health.hotspots[:5]],
            "recommendations": health.recommendations,
            "overview": overview.model_dump(),
            "critical_components": [],
            "flows": [],
            "database_tables": [],
            "api_routes": []
        }

        # Extract useful components to feed the LLM
        for g in components.groups:
            if g.key == "tables":
                evidence["database_tables"] = [{"id": c.id, "name": c.name} for c in g.items[:15]]
            elif g.key == "apis":
                evidence["api_routes"] = [{"id": c.id, "name": c.name, "route": c.route_path} for c in g.items[:15]]
            elif g.key == "services":
                evidence["critical_components"] = [{"id": c.id, "name": c.name} for c in g.items[:15]]
        
        for f in flows[:15]:
            evidence["flows"].append({
                "id": f.flow_id,
                "name": f.flow_name,
                "type": f.flow_type,
                "root_node_id": f.root_node.id
            })

        prompt = f"""You are a Senior Software Architect writing an interactive onboarding 'Story Mode' for a new developer.
You MUST write exactly 7 chapters based strictly on the provided GRAPH_EVIDENCE.
Return ONLY valid JSON matching this schema EXACTLY:
{{
  "repository_summary": "1-2 sentences summarizing the repo based on the evidence",
  "chapters": [
    {{
      "title": "Chapter Title",
      "content": "Narrative content (2-4 sentences explaining this aspect to a new dev)",
      "related_nodes": ["node_id_1", "node_id_2"],
      "related_flows": ["flow_id_1"]
    }}
  ]
}}

Required Chapters (in exact order):
1. What This Repository Does
2. How Requests Flow Through The System
3. Main Systems
4. Database Architecture
5. Critical Components
6. Architecture Risks
7. Recommended Learning Path

RULES:
- `related_nodes` MUST ONLY contain node "id" strings explicitly found in the GRAPH_EVIDENCE (e.g. from database_tables, api_routes, critical_components, or hotspots).
- `related_flows` MUST ONLY contain flow "id" strings explicitly found in the GRAPH_EVIDENCE's "flows" list.
- If no nodes or flows match a chapter, return an empty array [].
- DO NOT hallucinate business logic or nodes/flows that don't exist.
- Synthesize the health score, hotspots, and flows into the narrative.
- You are not just listing things; write a guided narrative!

GRAPH_EVIDENCE:
{json.dumps(evidence, indent=2)}
"""

        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=GROQ_MAX_TOKENS,
                    temperature=GROQ_TEMPERATURE,
                    response_format={"type": "json_object"}
                ),
            )
            text = resp.choices[0].message.content.strip()
            
            data = json.loads(text)
            
            # Reconstruct safely
            chapters = []
            for c in data.get("chapters", []):
                chapters.append(StoryChapter(
                    title=c.get("title", ""),
                    content=c.get("content", ""),
                    related_nodes=c.get("related_nodes", []),
                    related_flows=c.get("related_flows", [])
                ))
            
            return ArchitectureStory(
                repository_summary=data.get("repository_summary", "Architecture summary."),
                chapters=chapters
            )

        except Exception as e:
            logger.error(f"Failed to generate architecture story: {e}")
            # Deterministic Fallback
            return ArchitectureStoryService._fallback_story(evidence)

    @staticmethod
    def _fallback_story(evidence: dict) -> ArchitectureStory:
        chapters = [
            StoryChapter(
                title="What This Repository Does",
                content=f"This repository contains {evidence['overview'].get('total_files', 0)} files and {evidence['overview'].get('backend_services', 0)} backend services.",
                related_nodes=[],
                related_flows=[]
            ),
            StoryChapter(
                title="How Requests Flow Through The System",
                content="The repository processes API requests through various layers.",
                related_nodes=[],
                related_flows=[f["id"] for f in evidence["flows"][:3]]
            ),
            StoryChapter(
                title="Main Systems",
                content="The system consists of API routes and backend services.",
                related_nodes=[n["id"] for n in evidence["critical_components"][:5]],
                related_flows=[]
            ),
            StoryChapter(
                title="Database Architecture",
                content=f"There are {len(evidence['database_tables'])} database tables.",
                related_nodes=[t["id"] for t in evidence["database_tables"][:5]],
                related_flows=[]
            ),
            StoryChapter(
                title="Critical Components",
                content="Core components orchestrate the primary logic.",
                related_nodes=[n["id"] for n in evidence["critical_components"][:5]],
                related_flows=[]
            ),
            StoryChapter(
                title="Architecture Risks",
                content=f"Architecture Health is {evidence['architecture_health']} ({evidence['health_score']}/100).",
                related_nodes=[h["node_id"] for h in evidence["hotspots"][:5]],
                related_flows=[]
            ),
            StoryChapter(
                title="Recommended Learning Path",
                content="Start by exploring the API routes, then examine the core services.",
                related_nodes=[a["id"] for a in evidence["api_routes"][:3]],
                related_flows=[]
            )
        ]
        return ArchitectureStory(
            repository_summary="Deterministic fallback architecture summary.",
            chapters=chapters
        )
