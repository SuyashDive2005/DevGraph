# DevGraph

> **An Evolution-Aware Multi-Artifact Repository Knowledge Graph for Explainable Change-Impact Prediction**

DevGraph fuses structural (AST/imports/calls), semantic (embeddings/LLM), and historical (Git co-change) evidence into an explainable multi-artifact knowledge graph to predict change impact across software repositories without future temporal leakage.

---

## Architecture Overview

```
User Layer:        React UI (Repo Explorer · Impact Q&A · Evidence Panel)
                         │ (REST via FastAPI)
Reasoning Layer:   Weighted Impact Scoring → Calibrated Confidence → Evidence Bundle → LLM Explanation
                         │
Hybrid Retrieval:  Graph Traversal (Neo4j) · Semantic Search (Chroma) · History Co-change (SQLite)
                         │
Extraction:        Tree-sitter AST · Markdown/RST Parser · PyDriller Miner · Retrieve-then-Classify
                         │
Ingestion:         Git History Clone (pinned SHA) · GitHub API (Issues / Pull Requests)
```

---

## Quickstart (Week 1 Setup)

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Start Graph Database (Neo4j)
```bash
docker compose up -d
```
Neo4j browser will be available at `http://localhost:7474` (Bolt: `bolt://localhost:7687`, default auth: `neo4j` / `devgraph_pass`).

### 3. Ingest Pilot Repository
```bash
python scripts/index_repo.py --url pallets/click --stage ingest
```
This will:
- Clone full git history to `data/repos/click`
- Pin and record the HEAD commit SHA
- Fetch and cache GitHub issues and PRs to `data/github/click.json`

### 4. Run Tests
```bash
pytest tests/test_ingestion.py -v
```
