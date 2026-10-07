# DevGraph Implementation Progress

## Week 1 — Foundations, Ingestion, Environment
- **What was built:** Repo layout, `docker-compose.yml` (Neo4j Community 5.26), `devgraph/config.py`, typed Pydantic data models (`devgraph/models.py`), full-history Git cloner with SHA pinning (`devgraph/ingestion/clone.py`), paginated & cached GitHub metadata ingestion (`devgraph/ingestion/github_meta.py`), `scripts/repos.yaml`, `scripts/index_repo.py`, and `tests/test_ingestion.py`.
- **What broke & fixes:** Docker daemon initially required systemd socket activation (`systemctl start docker.socket`); `data/` directory created by Docker container defaulted to `nobody` ownership, resolved by chowning to local user (`1000:1000`) and enforcing proper folder permissions.
- **Numbers obtained:** Pilot repo `pallets/click` cloned with full history; HEAD SHA pinned at `2247b35ea1c47c727d7a06e51fa280e12a863ff6`; cached 10 issues and 10 PRs (configurable up to 300); Neo4j read/write verified; all 5 tests in `tests/test_ingestion.py` passed (100%).
- **Next phase:** Week 2 — Structural extraction (Tree-sitter AST, files, classes, functions, imports, calls) and building the first graph in Neo4j.
- **Notes & Viva defense:** Head commit SHA is pinned to ensure full evaluation reproducibility and enforce strict temporal isolation (preventing future information leakage).
