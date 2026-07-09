"""
Optimized graph traversal utilities for DevBrain production readiness.

Provides efficient, deterministic graph operations with caching and performance tracking.
"""

import logging
from typing import List, Set, Dict, Any, Optional
from collections import deque

from app.utils.logging_config import get_logger, log_performance
from app.utils.cache import cached, get_repository_cache
from app.utils.exceptions import GraphTraversalError

logger = get_logger(__name__)


class GraphOptimizer:
    """
    Optimized graph traversal with caching and performance tracking.
    
    Provides efficient BFS/DFS operations with:
    - Result caching
    - Early termination conditions
    - Deterministic ordering
    - Performance monitoring
    """
    
    def __init__(self):
        """Initialize graph optimizer."""
        self._traversal_stats = {
            "bfs_calls": 0,
            "dfs_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        logger.info("GraphOptimizer initialized")
    
    @log_performance(logger, "graph_bfs")
    def bfs(
        self,
        graph: Dict[str, List[str]],
        start: str,
        max_depth: int = 10,
        early_stop_condition: Optional[callable] = None
    ) -> List[str]:
        """
        Optimized BFS traversal with early termination.
        
        Args:
            graph: Adjacency list representation of graph
            start: Starting node
            max_depth: Maximum traversal depth
            early_stop_condition: Optional function to stop early
            
        Returns:
            List of visited nodes in BFS order
        """
        self._traversal_stats["bfs_calls"] += 1
        
        # Check cache
        cache_key = f"bfs_{start}_{max_depth}"
        cache = get_repository_cache()
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            self._traversal_stats["cache_hits"] += 1
            return cached_result
        
        self._traversal_stats["cache_misses"] += 1
        
        visited = set()
        queue = deque([(start, 0)])
        result = []
        
        while queue:
            node, depth = queue.popleft()
            
            if node in visited or depth > max_depth:
                continue
            
            visited.add(node)
            result.append(node)
            
            # Early stop condition
            if early_stop_condition and early_stop_condition(node, depth):
                break
            
            # Add neighbors (sorted for determinism)
            neighbors = sorted(graph.get(node, []))
            for neighbor in neighbors:
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        
        # Cache result
        cache.set(cache_key, result, ttl_seconds=300)
        
        return result
    
    @log_performance(logger, "graph_dfs")
    def dfs(
        self,
        graph: Dict[str, List[str]],
        start: str,
        max_depth: int = 10,
        early_stop_condition: Optional[callable] = None
    ) -> List[str]:
        """
        Optimized DFS traversal with early termination.
        
        Args:
            graph: Adjacency list representation of graph
            start: Starting node
            max_depth: Maximum traversal depth
            early_stop_condition: Optional function to stop early
            
        Returns:
            List of visited nodes in DFS order
        """
        self._traversal_stats["dfs_calls"] += 1
        
        # Check cache
        cache_key = f"dfs_{start}_{max_depth}"
        cache = get_repository_cache()
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            self._traversal_stats["cache_hits"] += 1
            return cached_result
        
        self._traversal_stats["cache_misses"] += 1
        
        visited = set()
        result = []
        
        def dfs_recursive(node: str, depth: int):
            if node in visited or depth > max_depth:
                return
            
            visited.add(node)
            result.append(node)
            
            # Early stop condition
            if early_stop_condition and early_stop_condition(node, depth):
                return
            
            # Visit neighbors (sorted for determinism)
            neighbors = sorted(graph.get(node, []))
            for neighbor in neighbors:
                dfs_recursive(neighbor, depth + 1)
        
        try:
            dfs_recursive(start, 0)
        except RecursionError:
            logger.error(f"DFS recursion depth exceeded for node {start}")
            raise GraphTraversalError("DFS recursion depth exceeded") from None
        
        # Cache result
        cache.set(cache_key, result, ttl_seconds=300)
        
        return result
    
    @log_performance(logger, "shortest_path")
    def shortest_path(
        self,
        graph: Dict[str, List[str]],
        start: str,
        end: str
    ) -> Optional[List[str]]:
        """
        Find shortest path between two nodes using BFS.
        
        Args:
            graph: Adjacency list representation of graph
            start: Starting node
            end: Target node
            
        Returns:
            List of nodes in shortest path, or None if no path exists
        """
        if start == end:
            return [start]
        
        # Check cache
        cache_key = f"path_{start}_{end}"
        cache = get_repository_cache()
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # BFS with path tracking
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            node, path = queue.popleft()
            
            if node == end:
                cache.set(cache_key, path, ttl_seconds=300)
                return path
            
            for neighbor in sorted(graph.get(node, [])):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        # No path found
        cache.set(cache_key, None, ttl_seconds=300)
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get traversal statistics."""
        total_calls = self._traversal_stats["bfs_calls"] + self._traversal_stats["dfs_calls"]
        cache_hit_rate = (
            self._traversal_stats["cache_hits"] / total_calls
            if total_calls > 0 else 0.0
        )
        
        return {
            **self._traversal_stats,
            "total_calls": total_calls,
            "cache_hit_rate": cache_hit_rate
        }


def ensure_deterministic_order(items: List[Any]) -> List[Any]:
    """
    Ensure deterministic ordering of items.
    
    Args:
        items: List of items to sort
        
    Returns:
        Sorted list for deterministic ordering
    """
    if not items:
        return []
    
    # Try to sort by string representation
    try:
        return sorted(items, key=lambda x: str(x))
    except Exception:
        # Fallback to original order if sorting fails
        return items


def normalize_graph(graph: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Normalize graph for deterministic operations.
    
    Args:
        graph: Adjacency list representation of graph
        
    Returns:
        Normalized graph with sorted neighbor lists
    """
    normalized = {}
    for node, neighbors in graph.items():
        normalized[node] = sorted(neighbors)
    
    return normalized


# Global graph optimizer instance
_graph_optimizer = GraphOptimizer()


def get_graph_optimizer() -> GraphOptimizer:
    """Get the global graph optimizer instance."""
    return _graph_optimizer
