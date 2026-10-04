# DevGraph

DevGraph builds an explainable knowledge graph of a Python repository to
support change-impact prediction.

## Starter status

This repository currently contains the Week 1 foundation:

- project/package layout
- environment configuration
- Neo4j Docker Compose setup
- Git repository cloning scaffold
- GitHub metadata caching scaffold
- repository selection configuration

Structural extraction, evolution mining, vector retrieval, scoring, evaluation,
LLM explanations, and the frontend will be added in later phases.

## Setup

The project uses a local Python virtual environment (`.venv`) compulsorily.
Do not install project dependencies into the system Python installation.

```powershell
. .\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
docker compose up -d
```

If PowerShell blocks local scripts, run this once for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Index a repository after adding its URL:

```powershell
.\.venv\Scripts\python.exe scripts/index_repo.py --url https://github.com/psf/requests.git --stage ingest
```

The repository is cloned under `data/repos/` and GitHub metadata is cached
under `data/github/`.
