"""
Configuration module for DevGraph.

Why this module exists:
Centralizes all environment variable loading, default path resolutions, and
connection credentials so no path or key is ever hardcoded across the codebase.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

# Base project directory
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Data storage paths
DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data"))).resolve()
REPOS_DIR: Path = DATA_DIR / "repos"
CHROMA_DIR: Path = DATA_DIR / "chroma"
EVOLUTION_DB_PATH: Path = DATA_DIR / "evolution.sqlite"
LLM_CACHE_DIR: Path = DATA_DIR / "llm_cache"
GITHUB_DIR: Path = DATA_DIR / "github"
NEO4J_DATA_DIR: Path = DATA_DIR / "neo4j"
RESULTS_DIR: Path = BASE_DIR / "results"

# GitHub credentials
GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")

# Neo4j configuration
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "devgraph_pass")

# LLM configuration
LLM_PROVIDER_BULK: str = os.getenv("LLM_PROVIDER_BULK", "groq")
LLM_MODEL_BULK: str = os.getenv("LLM_MODEL_BULK", "llama-3.3-70b-versatile")
LLM_PROVIDER_EXPLAIN: str = os.getenv("LLM_PROVIDER_EXPLAIN", "groq")
LLM_MODEL_EXPLAIN: str = os.getenv("LLM_MODEL_EXPLAIN", "llama-3.3-70b-versatile")
LLM_API_KEY_BULK: str = os.getenv("LLM_API_KEY_BULK", "")
LLM_API_KEY_EXPLAIN: str = os.getenv("LLM_API_KEY_EXPLAIN", "")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))

# Embeddings configuration
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def ensure_data_dirs() -> None:
    """Ensure all expected local storage directories exist on disk."""
    for directory in (
        DATA_DIR,
        REPOS_DIR,
        CHROMA_DIR,
        LLM_CACHE_DIR,
        GITHUB_DIR,
        NEO4J_DATA_DIR,
        RESULTS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
