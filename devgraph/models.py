"""
Data models for DevGraph.

Why this module exists:
Defines strictly typed Pydantic models for repository handles, graph nodes (Artifact),
graph relationships (Edge), scoring candidates, and evidence bundles. This ensures
type safety and consistent serialization across ingestion, extraction, and reasoning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RepoHandle(BaseModel):
    """
    Represents an ingested Git repository checkout pinned to a specific commit SHA.
    """
    path: Path
    head_sha: str
    name: str
    url: str


class Artifact(BaseModel):
    """
    Represents a node in the DevGraph knowledge graph.
    Common properties follow Section 7.1 of the specification.
    """
    id: str = Field(description="Unique node identifier: {repo}:{Type}:{path}")
    repo: str = Field(description="Repository name identifier")
    type: str = Field(description="Artifact type label e.g., File, Function, Commit")
    name: str = Field(description="Display or short name")
    path: str = Field(description="Relative path or qualified identifier")
    created_at: Optional[int | str] = Field(
        default=None, description="Creation timestamp or ISO string"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional type-specific properties"
    )


class Edge(BaseModel):
    """
    Represents a typed relationship between two Artifact nodes with provenance.
    Follows Section 7.2 of the specification.
    """
    src: str = Field(description="Source artifact ID")
    dst: str = Field(description="Target artifact ID")
    type: str = Field(description="Relationship type e.g., IMPORTS, CO_CHANGED_WITH")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0"
    )
    method: str = Field(
        default="ast", description="Extraction method: ast, git, naming_heuristic, llm:*"
    )
    source_commit: Optional[str] = Field(
        default=None, description="Snapshot or originating commit SHA"
    )
    timestamp: Optional[int] = Field(
        default=None, description="Timestamp when relationship was established"
    )
    is_deterministic: bool = Field(
        default=True, description="True if factually extracted; False if inferred"
    )
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional edge properties"
    )


class ScoredCandidate(BaseModel):
    """
    Represents a candidate impact file scored by the reasoning engine.
    """
    path: str
    score: float
    confidence: Optional[float] = None
    contributions: Dict[str, float] = Field(default_factory=dict)


class EvidenceBundle(BaseModel):
    """
    Evidence bundle packaging graph paths, co-change history, and linked edges
    for explainability. Follows Section 8 Week 6 specification.
    """
    seed: str
    candidate: str
    score: float
    confidence_calibrated: Optional[float] = None
    contributions: Dict[str, float] = Field(default_factory=dict)
    graph_path: List[str] = Field(default_factory=list)
    history: Dict[str, Any] = Field(default_factory=dict)
    linked_edges: List[Dict[str, Any]] = Field(default_factory=list)
