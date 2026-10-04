# DevGraph — Complete Implementation Guide (8-Week Plan)

> **Project title:** DevGraph — An Evolution-Aware Multi-Artifact Repository Knowledge Graph for Explainable Change-Impact Prediction
> **Team:** Kaivalya Deshpande, Suyash Dive, Riya Pande, Soham Patil | **Guide:** Mr. R. B. Murumkar
> **Purpose of this file:** (1) explain what the project IS, (2) give a step-by-step build plan that an AI coding agent (Antigravity) can execute phase by phase, (3) teach you enough that you can defend every line at the viva.

---

## 0. How to use this file

**For you (the humans):**
- Read Sections 1–3 fully *before* touching code. They are the "what and why".
- Each build phase in Section 8 has a **"Learn first"** box and an **"Explain-it-back"** question. If you can't answer the question in your own words, you don't understand that phase yet; do not move on.
- Keep a file `PROGRESS.md` in the repo. After every phase, write 5 lines: what was built, what broke, what numbers you got.

**For Antigravity (the AI agent) — give it these rules once at the start:**
1. Work on **one phase at a time** (Section 8). Never start a later phase.
2. Do **not** re-read the whole repository each time. Read only the files named in the task.
3. Before writing code for a phase, output a 10-line plan. After coding, run the tests listed in the phase's "Definition of Done" and paste the results.
4. Keep every module small and typed (Python type hints + pydantic). Add a docstring explaining *why* the module exists.
5. **Never call a paid LLM inside a loop without the disk cache** (Section 10.3). Never hard-code API keys or model names — read them from `.env`.
6. If a library API differs from what you remember (Tree-sitter, Chroma, Neo4j driver versions change often), **check the installed version's docs/`help()`** instead of guessing.
7. Do not build anything listed in Section 3.3 ("Do NOT build").

**Token-saving tips are in Section 13.** Read them before you start prompting.

---

## 1. What DevGraph actually is (plain English)

### 1.1 The problem
A software repository is not just code. It contains **code, tests, documentation, issues, pull requests, commits, and requirements**. But the *connections* between them are invisible. Nobody can look at a repo and instantly answer:

> "If I change `app.py`, **what else** might break or need updating — which other files, which tests, which docs?"

Today developers guess, or find out when something breaks. This is called **change-impact blindness**.

### 1.2 What we build
DevGraph reads a Git repository and builds a **knowledge graph** — a network where every file, class, function, test, doc section, commit, and issue is a **node**, and the relationships between them (calls, imports, tests, documents, modified-together) are **edges**.

Then, when a developer says *"I am going to change this file/function"*, DevGraph:
1. Finds candidate related artifacts using **three kinds of evidence**:
   - **Structural** — what calls/imports what (from parsing the code; 100% factual).
   - **Semantic** — what is *about* the same thing (from text embeddings and an LLM; probabilistic).
   - **Historical** — what has *actually been changed together in the past* (from Git history; our novelty).
2. Combines the three into a **single, explainable score** per candidate (a simple weighted formula — not a black box).
3. Returns a **ranked "impact report"** where every prediction comes with an **evidence panel**: the graph path, the past commits that changed both together, the score breakdown, and a plain-English explanation.

### 1.3 A concrete example
You are about to modify `flask/app.py`. DevGraph answers:

| Rank | Artifact | Score | Why |
|---|---|---|---|
| 1 | `tests/test_basic.py` | 0.91 | Imports `app.py` (structural, 1 hop) · co-changed with it in 14 of last 20 commits (historical) |
| 2 | `flask/helpers.py` | 0.78 | Imported by `app.py` (structural) · co-changed 9 times (historical) |
| 3 | `docs/quickstart.rst` | 0.55 | Semantically very similar to `app.py` docstrings (semantic) · co-changed 3 times |

The point is not only the *list* — it is that **you can inspect why**, so you can trust (or reject) each item.

### 1.4 What is NEW here (your research contribution)
Each of the 11 papers in your survey uses structural and/or semantic evidence on a **static snapshot**. **None** fuse them with **Git history**, and none enforce a **"no future information" evaluation protocol**. So the honest contribution is:

1. **Integration:** structural + semantic + historical evidence fused in one graph.
2. **Evaluation rigor:** a *temporal leakage-free* test ("predict a past commit using only what existed before it").
3. **Explainability:** every edge carries confidence + provenance; the LLM only *explains*, never *invents* facts.

> ⚠️ **Do not claim** you invented KGs, embeddings, or LLM prompting. The claim is *integration + evaluation*. A **negative result** (history does not help) is still a valid, honest result — that's what the ablations test.

### 1.5 The central research question (memorise this)
> *Does fusing structural + semantic + historical evidence predict change impact better than any single evidence source — and can every prediction be explained with inspectable evidence?*

---

## 2. Concepts you must understand (read before coding)

| Concept | One-paragraph explanation | Where we use it |
|---|---|---|
| **Knowledge graph (KG)** | Data stored as nodes + typed edges instead of tables. Great for "what is connected to what, and how far away". | Neo4j |
| **AST (Abstract Syntax Tree)** | A tree representation of source code produced by a parser. Lets us find classes, functions, imports, calls *deterministically* — no guessing. | Tree-sitter |
| **Tree-sitter** | A fast parser library that produces ASTs for many languages. | Structural extraction |
| **Co-change (change coupling)** | Two files that are frequently modified in the *same commit* are probably related, even if no import links them. Strength ≈ `commits touching both / commits touching the seed`. | Evolution Miner |
| **Embedding** | A vector (list of numbers) representing the *meaning* of a text. Similar meaning → vectors close together (cosine similarity). | Semantic evidence |
| **Vector DB (Chroma)** | A database that finds the nearest vectors fast. | Semantic retrieval |
| **RAG (Retrieval-Augmented Generation)** | Instead of asking an LLM from memory, first *retrieve* relevant evidence, then ask the LLM to use only that evidence. | Semantic edges + explanations |
| **Retrieve-then-classify** | Stage 1: embeddings fetch top-k candidate pairs cheaply. Stage 2: LLM judges each pair yes/no + confidence. Used by papers P2, P4, P10. | Semantic edge extraction |
| **Deterministic vs inferred edge** | Deterministic = proven by parsing (call, import). Inferred = a model's judgment (this issue is implemented by that function). We **store which is which**. | Provenance model |
| **Provenance / confidence** | Every edge stores *how* it was created, *when*, from *which commit*, and *how sure* we are. | Explainability |
| **Terminal-KG principle (P6)** | The LLM must never state a repo fact the graph hasn't verified. It only rephrases verified evidence. | Explanation module |
| **Temporal leakage** | Accidentally using information from *after* the event you're predicting (e.g., using the future commit's own co-change data to "predict" it). Inflates results. | Evaluation |
| **Precision / Recall / F1 / F2** | Precision = of what we predicted, how much was right. Recall = of what was right, how much we found. F2 weights recall 2× more than precision (missing an impacted file is worse than a false alarm). | Evaluation |
| **Ablation** | Remove one component and re-measure to prove it matters. | Evaluation |
| **Baseline** | A simpler competitor method to beat. | Evaluation |
| **Wilcoxon signed-rank test** | A statistical test to check if method A is *significantly* better than method B over many scenarios. | Evaluation |

---

## 3. Scope decisions (important — read carefully)

Your report's verdict was **MODIFY**: keep the core, cut the risky extras. Because we now have **~8 weeks instead of 2 semesters**, the scope is cut further. **Show this section to your guide** so the reductions are agreed.

### 3.1 MUST BUILD (the minimum that makes the project a success)
1. Ingestion: clone repo, pin commit hash, pull issues/PRs via GitHub API.
2. Structural extraction (Python code only) with Tree-sitter → files/classes/functions/imports/calls.
3. Evolution Miner (PyDriller) → commit history + co-change statistics.
4. Knowledge graph in Neo4j with the provenance model.
5. Vector index (Chroma) of files + docs + issues.
6. Hybrid retrieval (graph + vector + history).
7. Interpretable weighted impact scoring + calibrated confidence.
8. Evidence bundle + constrained LLM explanation (with a verification gate).
9. Evaluation harness: temporal leakage-free, 3 baselines, 2 ablations, statistics.
10. Minimal API (FastAPI) + minimal UI (React) showing the graph and the evidence panel.

### 3.2 SHOULD BUILD (only if the MUST list is done by end of Week 6)
- Traceability sub-engine: issue → code → test links with LLM classification.
- CM1 public-benchmark sanity check (reuse numbers from papers P2/P3/P10).

### 3.3 Do NOT build (explicitly out of scope)
- ❌ Documentation-drift detection and architecture-drift detection. *No paper in your survey validates a method; your own slide says "Out-of-Scope (Stretch Goals)".* Mention them only as **Future Work**.
- ❌ GNNs / model training / fine-tuning. (P5 shows simpler models are competitive; also no GPU.)
- ❌ Multi-language support. **Python repos only.**
- ❌ AI "change planner", IDE/CI plugins, multi-repo graphs, authentication, deployment to cloud.

### 3.4 Differences from your PPT/report (and why)

| Report/PPT said | This plan does | Reason |
|---|---|---|
| 3–5 repositories | **2 repositories** (3rd only if ahead of schedule) | 8 weeks |
| 15–20 *manually* labelled scenarios per repo | **~50 automatically-labelled scenarios per repo** (ground truth = other files changed in the same real commit), + **manual sanity check of 10 per repo** | Manual labelling is the #1 schedule risk in your own report |
| 13 node types | Implement ~9 now (see 7.1); schema stays extensible | Time |
| Gemini 1.5 Flash / GPT-4o-mini | **Provider-agnostic LLM client; models set in `.env`**. Slides mention Groq API, so default to Groq's free tier for bulk classification and any Gemini/OpenAI model for explanations | Model names in the report may be outdated — check the provider's current model list |
| Temporal protocol by checking out parent commit per scenario | **Single "as-of" snapshot protocol** (Section 11.2) | Far cheaper, still leak-free |
| Traceability on 3–4 public benchmarks | **CM1 only**, optional | Your report itself recommends this for small teams |

> ⚠️ **Honest limitation to state in your report:** using "files changed in the same commit" as ground truth is a *proxy* (a developer may have forgotten to change a file, or changed unrelated files together). We reduce this risk by filtering noisy commits and manually reviewing a sample.

---

## 4. Architecture

### 4.1 Layers (matches your slide)

```
                ┌────────────────────────── USER LAYER ───────────────────────────┐
                │  React UI: Repo Explorer · Impact Q&A · Evidence Panel (Cytoscape)│
                └───────────────────────────────▲──────────────────────────────────┘
                                                │ REST (FastAPI)
                ┌───────────────────────────────┴──────────────────────────────────┐
                │ REASONING LAYER: Impact Scoring (weighted) → Confidence →          │
                │                  Evidence Bundle → LLM Explanation (+ verify gate) │
                └───────────────────────────────▲──────────────────────────────────┘
                ┌───────────────────────────────┴──────────────────────────────────┐
                │ HYBRID RETRIEVAL: Graph traversal | Vector search | Historical    │
                └──────▲───────────────────────▲──────────────────────▲────────────┘
                       │                       │                      │
              ┌────────┴───────┐      ┌────────┴────────┐    ┌────────┴────────┐
              │ Neo4j (KG)     │      │ Chroma (vectors)│    │ SQLite (history)│
              └────────▲───────┘      └────────▲────────┘    └────────▲────────┘
                       │                       │                      │
                ┌──────┴───────────────────────┴──────────────────────┴───────────┐
                │ EXTRACTION: Tree-sitter AST | Doc parser | PyDriller miner | LLM  │
                │ semantic linker (retrieve-then-classify)                          │
                └───────────────────────────────▲──────────────────────────────────┘
                ┌───────────────────────────────┴──────────────────────────────────┐
                │ INGESTION: GitPython clone (pinned SHA) + GitHub API (issues/PRs) │
                └──────────────────────────────────────────────────────────────────┘
        OFFLINE:  Evaluation Module (scenarios · baselines · ablations · metrics · leakage check)
```

### 4.2 The "Evolution DB" decision
Your slide says "Neo4j/SQL". **Use SQLite** for raw commit data (`commits`, `commit_files`) and compute co-change with SQL *as of any cutoff time*. This makes the temporal protocol trivial (`WHERE ts < :cutoff`). Also write the aggregated `CO_CHANGED_WITH` edges into Neo4j for the UI/visualisation only.

### 4.3 Design discipline (the rules that make this a research project, not a demo)
1. Structural facts come from the **parser**, never the LLM.
2. The LLM may only (a) classify candidate pairs *given retrieved text*, and (b) explain *already-computed* evidence.
3. The impact score is computed **before** any explanation call and contains **no LLM arithmetic**.
4. Every edge stores `confidence`, `method`, `source_commit`, `timestamp`, `is_deterministic`.
5. Every evaluation scenario passes the **leakage check** or it is discarded.

---

## 5. Tech stack and setup

| Layer | Tool | Notes |
|---|---|---|
| Language | Python 3.11+ | Everything backend |
| API | FastAPI + Pydantic + Uvicorn | |
| Graph DB | Neo4j **Community** (Docker) | Community edition has **only one user database** → separate repos by a `repo` property, not by database |
| Vector DB | Chroma (persistent, embedded) | One collection per repo |
| History DB | SQLite (stdlib `sqlite3`) | |
| Code parsing | `tree-sitter` + `tree-sitter-python` | Check installed version's API |
| Git mining | `PyDriller` (+ `GitPython`) | |
| Embeddings | `sentence-transformers`, model `all-MiniLM-L6-v2` (fast, CPU) | Optional upgrade: `all-mpnet-base-v2` |
| LLM | Provider-agnostic wrapper over OpenAI-compatible endpoints (Groq, Gemini via OpenAI-compat, OpenAI, or local Ollama) | Models in `.env` |
| ML/metrics | `scikit-learn`, `scipy`, `numpy`, `pandas` | Metrics, isotonic calibration, Wilcoxon |
| Frontend | React (Vite) + `cytoscape` (via `react-cytoscapejs`) | |
| Infra | Docker Compose (Neo4j only is mandatory) | |
| Tests | `pytest` | |

**Hardware:** 4-core CPU, 8 GB RAM, 20 GB disk is enough; no GPU.

**`.env.example`** (Antigravity must create this and never commit the real `.env`):
```
GITHUB_TOKEN=
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=devgraph_pass
LLM_PROVIDER_BULK=groq            # cheap model for classification
LLM_MODEL_BULK=<check provider docs>
LLM_PROVIDER_EXPLAIN=groq         # or gemini/openai
LLM_MODEL_EXPLAIN=<check provider docs>
LLM_API_KEY_BULK=
LLM_API_KEY_EXPLAIN=
LLM_TEMPERATURE=0
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
DATA_DIR=./data
```

---

## 6. Repository layout (Antigravity must create exactly this)

```
devgraph/
├── docker-compose.yml            # Neo4j service
├── .env.example
├── requirements.txt
├── README.md
├── PROGRESS.md                   # human-maintained log
├── data/                         # gitignored: repos/, chroma/, evolution.sqlite, llm_cache/, github/
├── devgraph/
│   ├── config.py                 # loads .env, paths
│   ├── models.py                 # pydantic: Artifact, Edge, EvidenceBundle, ScoredCandidate
│   ├── ingestion/
│   │   ├── clone.py              # clone + pin SHA
│   │   └── github_meta.py        # issues/PRs → data/github/{repo}.json
│   ├── extraction/
│   │   ├── structural.py         # Tree-sitter: files/classes/functions/imports/calls
│   │   ├── resolver.py           # import → file path resolution
│   │   ├── docs.py               # md/rst → DocSection nodes
│   │   └── semantic.py           # retrieve-then-classify (LLM) → inferred edges
│   ├── evolution/
│   │   ├── miner.py              # PyDriller → SQLite
│   │   └── cochange.py           # as-of co-change queries
│   ├── graph/
│   │   ├── neo4j_store.py        # batch writers, constraints
│   │   └── queries.py            # Cypher: neighbors, paths, links
│   ├── vector/
│   │   ├── embedder.py
│   │   └── chroma_store.py
│   ├── llm/
│   │   ├── client.py             # provider-agnostic + retries
│   │   ├── cache.py              # disk cache keyed by hash(model+prompt)
│   │   └── prompts.py            # all prompt templates (versioned)
│   ├── retrieval/hybrid.py       # 3-leg candidate generation
│   ├── reasoning/
│   │   ├── scoring.py            # weighted impact score
│   │   ├── calibration.py        # isotonic confidence
│   │   ├── evidence.py           # build EvidenceBundle
│   │   └── explain.py            # LLM explanation + verification gate
│   ├── eval/
│   │   ├── scenarios.py          # pick/label commits, dev/test split
│   │   ├── baselines.py          # static-only, vector-only, LLM-only
│   │   ├── metrics.py            # P/R/F1/F2/P@k/R@k/MAP, ECE
│   │   ├── leakage_check.py
│   │   ├── run_eval.py           # full + ablations + stats → results/*.csv
│   │   └── traceability_cm1.py   # optional
│   └── api/main.py               # FastAPI app
├── frontend/                     # Vite + React
├── scripts/                      # index_repo.py, run_eval.sh
├── results/                      # CSVs, figures, tables used in the report
└── tests/
```

---

## 7. Data model (knowledge graph schema)

### 7.1 Node types (implement these now)
All nodes have label `:Artifact` **plus** a type label. Common properties: `id` (unique), `repo`, `type`, `name`, `path`, `created_at`.

| Type label | Extra properties | Created by |
|---|---|---|
| `Repository` | `url`, `snapshot_sha` | ingestion |
| `File` | `path`, `language`, `loc`, `is_test`, `is_doc` | structural |
| `Class` | `qualname`, `file`, `start_line`, `end_line` | structural |
| `Function` | `qualname`, `file`, `start_line`, `end_line`, `is_method` | structural |
| `DocSection` | `file`, `heading`, `text` | docs |
| `Commit` | `sha`, `ts`, `author`, `message` | miner |
| `Issue` | `number`, `title`, `body`, `created_at`, `state` | GitHub |
| `PullRequest` | `number`, `title`, `body`, `created_at` | GitHub |
| `Requirement` | `text`, `source_issue`, `is_inferred=true` | semantic (inferred from issues) |

(`Test` = a `File`/`Function` with `is_test=true`. `API`, `ArchitectureDecision`, `Release` from the report are deferred — schema allows adding them.)

**ID convention:** `{repo}:{Type}:{path}` and `{repo}:Function:{path}::{qualname}` — e.g. `flask:File:src/flask/app.py`.

### 7.2 Relationship types
| Edge | From → To | Deterministic? | Created by |
|---|---|---|---|
| `CONTAINS` | Repository/File → File/Class/Function | yes | structural |
| `DEFINES` | File → Class/Function; Class → Function | yes | structural |
| `IMPORTS` | File → File | yes | structural |
| `CALLS` | Function → Function (best-effort name resolution) | yes* | structural |
| `DEPENDS_ON` | File → File (derived from IMPORTS/CALLS) | yes | structural |
| `MODIFIES` | Commit → File | yes | miner |
| `FIXES` | Commit → Issue (from "fixes #123" in message) | yes | miner |
| `CO_CHANGED_WITH` | File ↔ File (props: `count`, `support`, `confidence`) | yes (statistical) | miner |
| `VERIFIES` | Test File → File/Function | **no** (naming heuristic, LLM) | semantic |
| `DOCUMENTS` | DocSection → File/Function | **no** | semantic |
| `IMPLEMENTS` | File/Function → Requirement | **no** | semantic |

\* Python call resolution by name is approximate. State this limitation.

**Every edge property set:** `confidence` (0–1), `method` (`ast` / `git` / `naming_heuristic` / `llm:{model}`), `source_commit`, `timestamp`, `is_deterministic` (bool). Deterministic edges get `confidence=1.0`.

### 7.3 Cypher setup (run at startup)
```cypher
CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (n:Artifact) REQUIRE n.id IS UNIQUE;
CREATE INDEX artifact_repo IF NOT EXISTS FOR (n:Artifact) ON (n.repo);
CREATE INDEX artifact_path IF NOT EXISTS FOR (n:Artifact) ON (n.path);
```
**Writing tip:** Cypher cannot parameterise relationship *types*. Group edges by type in Python and run one `UNWIND $rows AS r MATCH (a:Artifact {id:r.src}) MATCH (b:Artifact {id:r.dst}) MERGE (a)-[e:IMPORTS]->(b) SET e += r.props` per type, in batches of ~1,000.

### 7.4 SQLite schema (Evolution DB)
```sql
CREATE TABLE commits(sha TEXT PRIMARY KEY, ts INTEGER, author TEXT, message TEXT, n_files INTEGER, is_merge INTEGER);
CREATE TABLE commit_files(sha TEXT, path TEXT, change_type TEXT, added INTEGER, deleted INTEGER);
CREATE INDEX idx_cf_path ON commit_files(path);
CREATE INDEX idx_cf_sha  ON commit_files(sha);
CREATE INDEX idx_c_ts    ON commits(ts);
```

---

## 8. Phase-by-phase build plan (8 weeks)

> **Rhythm:** each phase ends with a **Definition of Done (DoD)** you can verify. If a phase overruns by more than 2 days, use the cut list in Section 14 — don't let it eat the next phase.
>
> **Team split (optional, 4 people):** A = Ingestion + Structural + Miner · B = LLM client + Semantic + Vector · C = Graph store + Scoring + Evidence/Explain · D = Evaluation + API/UI. In practice, **Antigravity writes the code; you each own and must explain one area.**

---

### WEEK 1 — Foundations, ingestion, environment

**Learn first:** What is a Git commit/SHA; what Docker Compose does; what a Neo4j node/relationship is; run 5 basic Cypher queries in the Neo4j browser (`MATCH`, `CREATE`, `MERGE`, `RETURN`, `WHERE`).

**Tasks**
1. Create the repo layout (Section 6), `requirements.txt`, `.env.example`, `.gitignore` (ignore `data/`, `.env`).
2. `docker-compose.yml` with Neo4j Community (ports 7474, 7687, auth from env, volume for persistence). Verify with `docker compose up -d` and connect via the Python driver.
3. `config.py`: load `.env`, expose paths (`data/repos`, `data/chroma`, `data/evolution.sqlite`, `data/llm_cache`).
4. `ingestion/clone.py`: `clone(url) -> RepoHandle(path, head_sha)`; clone full history (no `--depth`), record `head_sha`.
5. `ingestion/github_meta.py`: fetch up to ~300 most recent **issues** and ~300 **PRs** (title, body, number, created_at, closed_at, state, labels) with the token, paginate, respect rate limits, save to `data/github/{repo}.json`. Cache; don't refetch if file exists.
6. **Choose repositories** (see 8.0.1 below) and write them into `scripts/repos.yaml`.

**8.0.1 Repository selection criteria** (from your report, Phase 9): public, Python, **10K–150K LOC**, ≥ ~800 commits, has a `tests/` folder, has docs (README + `docs/`), active issues/PRs. Candidates in the right size class: `pallets/click`, `psf/requests`, `pallets/flask`, `encode/httpx`. **Verify each against the criteria yourselves** (commit count, LOC via `cloc`, license) before freezing. Start with **one pilot repo** (smallest), add the second in Week 5.

**DoD**
- `docker compose up` works; a test script writes and reads one node.
- `python scripts/index_repo.py --url <repo> --stage ingest` clones and saves GitHub JSON.
- `pytest tests/test_ingestion.py` passes.

**Explain-it-back:** *Why do we pin the commit SHA?* (Reproducibility + needed for the temporal protocol.)

**Antigravity prompt:** "Implement Week 1 of DEVGRAPH_IMPLEMENTATION_GUIDE.md only (Sections 5, 6, 8-Week 1). Output a plan first. Do not implement later weeks."

---

### WEEK 2 — Structural extraction → first graph in Neo4j

**Learn first:** What an AST is (print one with Tree-sitter for a 10-line Python file); the difference between *definition*, *import*, and *call* nodes; why name-based call resolution is approximate.

**Tasks**
1. `extraction/structural.py`: for each `.py` file (skip `venv`, `build`, `node_modules`, vendored, generated files; strip > 1 MB files), parse with Tree-sitter and extract:
   - `Class` and `Function` (incl. methods, with `qualname`, start/end lines),
   - imports (`import x`, `from x import y`, relative imports),
   - call expressions (callee *name*).
2. `extraction/resolver.py`: build a map `dotted module name → file path` from the directory layout (handle `src/` layout and packages with `__init__.py`; resolve relative imports using the importing file's package). Only keep imports that resolve to files **inside** the repo (ignore third-party).
3. Build edges: `CONTAINS`, `DEFINES`, `IMPORTS` (File→File), `CALLS` (Function→Function when the name resolves to a function in the same file or an imported symbol; otherwise drop), and derive `DEPENDS_ON` (File→File) from IMPORTS (+ CALLS across files).
4. Mark `is_test=true` for files under `tests/`/`test/` or named `test_*.py` / `*_test.py`.
5. `graph/neo4j_store.py`: batch `MERGE` writers for nodes and edges with the provenance properties (Section 7.2). `source_commit` = snapshot SHA, `timestamp` = snapshot commit time.
6. Print stats: #files, #classes, #functions, #IMPORTS, #CALLS, % imports resolved.

**DoD**
- Pilot repo graph is visible in the Neo4j browser (`MATCH (f:File)-[:IMPORTS]->(g:File) RETURN f,g LIMIT 50`).
- Unit tests on 3 tiny fixture Python files with known imports/calls pass (e.g., a→b import, a.foo calls b.bar).
- Resolved-import rate on the pilot repo is reported; investigate if < 80% (usually a package-root bug).

**Explain-it-back:** *Why is `CALLS` marked deterministic but with a footnote?* (The parse is deterministic; resolving a Python name to its target is best-effort because of dynamic typing.)

---

### WEEK 3 — Evolution Miner (the novelty) + temporal "as-of" queries

**Learn first:** Co-change/change-coupling concept; association-rule vocabulary (*support*, *confidence*); why bulk commits (e.g., 200-file reformat) poison co-change statistics.

**Tasks**
1. `evolution/miner.py`: use PyDriller to walk all commits on the main branch; skip merge commits; for each, store `sha, ts, author, message, n_files` and each modified file (`new_path`, change type, added/deleted lines) in SQLite. (Renames: track `new_path`; document the limitation.)
2. **Noise filters** (store everything, filter at query time via config): ignore commits touching `> 30` files (bulk refactors/releases); ignore files like `CHANGES*`, `CHANGELOG*`, `*.lock`, version/metadata files, `docs/_build`, binaries. These are standard in co-change mining; state them in your report.
3. `evolution/cochange.py` — **the key function:**
   ```python
   def cochange(seed_path: str, cutoff_ts: int, half_life_days: int = 180) -> dict[str, CoChange]:
       """
       Only commits with ts < cutoff_ts are considered (temporal protocol).
       For each other file g changed together with seed:
         co_w   = sum over shared commits of 2^(-(cutoff_ts - ts)/half_life)
         seed_w = sum over all commits touching seed of the same decay weight
         confidence = co_w / seed_w            # in [0,1]
         also return raw count, last_cochange_ts, and the list of up to 5 evidence commit SHAs
       """
   ```
   Implement with one SQL self-join on `commit_files` + Python decay weights; make it fast with the indexes.
4. Link commits to issues: regex for `(fix(es|ed)?|close[sd]?|resolve[sd]?)\s+#(\d+)` and `(#\d+)` in messages → `FIXES`/`DISCUSSES` edges (deterministic).
5. Write `Commit` nodes + `MODIFIES` edges + aggregated `CO_CHANGED_WITH` edges (as of **HEAD**) to Neo4j *for visualisation*. (Evaluation uses SQLite `cochange()`, not these edges.)

**DoD**
- Miner indexes the pilot repo (log: #commits, #commit_files).
- `cochange("src/<some_file>.py", cutoff_ts=<some past ts>)` returns plausible neighbours; a unit test proves that **a commit with `ts >= cutoff` never contributes** (insert a synthetic future commit and assert it is ignored).
- Spot-check 5 top co-change pairs manually — do they make sense?

**Explain-it-back:** *Why divide by the seed's count and not the total commits?* (We want P(candidate changes | seed changes), a conditional probability.)

---

### WEEK 4 — Vector index, hybrid retrieval, first two baselines

**Learn first:** Embeddings and cosine similarity (try `model.encode` on 3 sentences); what Chroma stores (id, vector, metadata, document); why file text must be chunked/truncated.

**Tasks**
1. `extraction/docs.py`: split `.md`/`.rst` docs and the README into `DocSection` nodes by headings (Markdown `#`; RST underline-style headings via a simple regex). Cap section text at ~1,500 characters.
2. `vector/embedder.py` + `vector/chroma_store.py`: embed
   - **File documents:** `path + module docstring + class/function names + first ~100 lines`, truncated to the model's max length (do **not** embed 5,000-line files raw),
   - **DocSection** text,
   - **Issue/PR** title + body (truncate),
   with metadata `{repo, type, path, created_at}`. Persist in `data/chroma`. Batch encode (CPU is fine).
3. `graph/queries.py`: Cypher helpers:
   - `structural_neighbors(file_id, max_depth=3)` → candidates with distance and direction (dependents vs dependencies),
   - `tests_for(file_id)`.
4. `retrieval/hybrid.py`: `retrieve(repo, seed_path, as_of_ts, k=30) -> CandidatePool` returning three lists, each tagged with its evidence type:
   - **graph leg** (structural neighbours),
   - **vector leg** (top-k most similar *File/DocSection* by cosine, `created_at <= as_of_ts` filter on metadata),
   - **history leg** (`cochange()` top-k).
   Then union into one pool: `{candidate_path: {struct: ..., sem: ..., hist: ..., links: ...}}`. **Candidates are file-level** (DocSections roll up to their file).
5. `eval/baselines.py` (first two): `static_only(seed)` ranks by structural score only; `vector_only(seed)` ranks by cosine only.

**DoD**
- `retrieve()` on 3 sample files returns sensible three-leg output; print it as a table.
- Metadata filter works: querying with an old `as_of_ts` never returns later-created issues/docs.
- Tests for each leg.

**Explain-it-back:** *Why keep three separate retrieval legs instead of one big vector search?* (Different evidence types; keeps each cheap and bounded; and lets ablations remove one at a time.)

---

### WEEK 5 — Scoring model + evaluation harness (**first real numbers this week**)

> This is the most important week. If you only get Weeks 1–5 done well, you already have a defensible project.

**Learn first:** Precision/Recall/F1/F2 by hand on a 10-item example; what MAP is; train/dev/test split and why we tune weights *only* on dev; Wilcoxon test.

**Tasks**

1. **`reasoning/scoring.py`** — interpretable scoring (Section 9 has the exact formula). Returns for each candidate: `total`, per-signal contributions, and the evidence needed later.
2. **`eval/scenarios.py`** — build the evaluation set (Section 11.3 has the exact procedure) and save as `results/{repo}_scenarios.json` (frozen; commit it to Git).
3. **`eval/leakage_check.py`** — for each scenario assert programmatically: (a) every history row used has `ts < scenario_ts`; (b) every issue/PR/doc used has `created_at < scenario_ts`; (c) the scenario's own commit never appears in the evidence. A scenario that fails is **dropped and counted**.
4. **`eval/metrics.py`** — `precision, recall, f1, f2, precision_at_k, recall_at_k, average_precision` + calibration error (Section 11.5). Add unit tests with tiny hand-computed examples.
5. **`eval/run_eval.py`** — for each scenario and each method (static-only, vector-only, history-only [bonus], full, no-history, code-only), produce a ranked list; compute metrics; write `results/{repo}_per_scenario.csv` and `results/{repo}_summary.csv`.
6. **Tune weights on the dev split only** (small grid search, Section 9.3), freeze them in `results/weights.json`, then evaluate on the test split.
7. Add the **second repository** (ingest + structural + miner + vector) now, so Weeks 6–8 can run on both.

**DoD**
- `python -m devgraph.eval.run_eval --repo pilot` prints a table: methods × (P@5, R@5, F2, MAP) on the test split.
- You can say, in one sentence, whether history helped on the pilot repo. (Either answer is fine — report it honestly.)

**Explain-it-back:** *Why tune weights on dev and report on test?* (Tuning on the same data you report on inflates results — another form of leakage.)

---

### WEEK 6 — LLM semantic linking, provenance, evidence + explanation

**Learn first:** What a prompt template is; temperature=0 and why LLM outputs are still not perfectly reproducible; JSON-constrained output; the terminal-KG principle (P6).

**Tasks**
1. **`llm/client.py`**: one function `complete(prompt, role="bulk"|"explain", json_mode=False) -> str` with retries/backoff, timeout, and rate-limit sleep (free tiers rate-limit hard). **`llm/cache.py`**: before any call, look up `sha256(provider+model+prompt+temperature)` in `data/llm_cache/`; store every response. This both saves tokens and makes evaluation reproducible.
2. **`llm/prompts.py`**: the templates in Section 10.
3. **`extraction/semantic.py`** — retrieve-then-classify with a **hard budget** (≤ ~1,500 LLM calls per repo; cap candidates):
   - **Test→code `VERIFIES`:** first a *naming heuristic* (`tests/test_x.py` ↔ `x.py`, conf 0.7, `method=naming_heuristic`); then LLM-classify only the ambiguous top-3 imports-based candidates.
   - **Doc→code `DOCUMENTS`:** for each DocSection, vector top-5 files → LLM classify.
   - **Requirement→code `IMPLEMENTS`:** for the ~100 most recent *closed* issues, create a `Requirement` node (`is_inferred=true`) from title+body; link to files via (a) **deterministic** `FIXES` commits → `MODIFIES` files (confidence 1.0, `method=git`) and (b) LLM-classified vector top-5 for issues without linked commits.
   - Store all edges with the full provenance property set. Drop LLM edges with `confidence < 0.5` (configurable).
   - **For evaluation fairness:** every semantic edge must carry the `created_at` of the *newest* artifact involved so the leakage check can exclude edges not yet existing at scenario time.
4. **`reasoning/calibration.py`**: fit an isotonic regression (scikit-learn) mapping `total score → empirical hit rate` on the **dev** split; apply on test. Save the model with `joblib`.
5. **`reasoning/evidence.py`**: `build_bundle(seed, candidate, as_of_ts)` → `EvidenceBundle`:
   ```json
   {
     "seed": "src/flask/app.py", "candidate": "tests/test_basic.py",
     "score": 0.91, "confidence_calibrated": 0.84,
     "contributions": {"structural": 0.35, "historical": 0.31, "semantic": 0.13, "links": 0.12},
     "graph_path": ["File:tests/test_basic.py -IMPORTS-> File:src/flask/app.py"],
     "history": {"co_changes": 14, "support": 20, "evidence_commits": [{"sha": "ab12cd3", "date": "2023-04-02", "msg": "..."}]},
     "linked_edges": [{"type": "VERIFIES", "confidence": 0.7, "method": "naming_heuristic"}]
   }
   ```
6. **`reasoning/explain.py`** — LLM explanation **with a verification gate** (Section 10.4): the LLM sees *only* the bundle; afterwards, code verifies every file path and SHA mentioned in the output appears in the bundle. If not → discard and fall back to a deterministic template sentence.
7. **LLM-only baseline** (`eval/baselines.py`): see Section 11.4; run it now so Week 8 only runs the full evaluation.
8. *(SHOULD, if on schedule)* **`eval/traceability_cm1.py`**: download CM1 (requirements ↔ design) from the CoEST benchmark repository (search for "CoEST CM1 dataset"; also available through replication packages of the LiSSA/TraceLLM papers — verify the source and license), embed elements, retrieve top-k, LLM-classify, compute F2, compare with the 0.68 reported in P3 as a **sanity reference** (not a "we beat them" claim).

**DoD**
- Neo4j contains `VERIFIES`/`DOCUMENTS`/`IMPLEMENTS` edges with provenance; a Cypher query shows `is_deterministic=false` edges with `method` and `confidence`.
- Re-running the semantic stage costs **0 LLM calls** (cache hits) — prove it.
- Explanation gate test: feed a deliberately fabricated explanation containing a non-existent path → gate rejects it.
- Calibration plot/ECE computed on test.

**Explain-it-back:** *What stops the LLM from hallucinating a dependency?* (It never creates facts: edges come from the parser/Git; LLM edges are labelled inferred with confidence; explanations are checked against the bundle.)

---

### WEEK 7 — API + minimal UI

**Learn first:** REST basics, FastAPI path/query/body models, how Cytoscape renders nodes/edges from JSON.

**Tasks**
1. **`api/main.py`** (FastAPI, CORS enabled for the Vite dev server):
   - `GET /repos` → indexed repos + stats.
   - `GET /graph/neighbors?repo=&id=&depth=1` → nodes+edges JSON (cap 200 nodes).
   - `POST /impact` body `{repo, seed_path | commit_sha, as_of?: iso-date}` → ranked list (top 15) with score breakdown and calibrated confidence. If `commit_sha` is given, use its **parent time** as `as_of` and its changed source file(s) as seeds.
   - `GET /evidence?repo=&seed=&candidate=` → `EvidenceBundle` + LLM explanation (cached).
   - `POST /index` → kicks off indexing for a URL as a background task and exposes `GET /index/status`.
2. **Frontend (keep it small — 3 views):**
   1. **Repo Explorer:** search a file; Cytoscape view of its neighbourhood, nodes coloured by type, edges styled **solid = deterministic, dashed = inferred**, with confidence on hover.
   2. **Impact Query:** input a file path (autocomplete) or commit SHA → ranked table with a **stacked bar** per row (structural/historical/semantic/links).
   3. **Evidence Panel:** click a row → graph path, list of evidence commits, calibrated confidence, and the explanation text with a badge "verified against evidence".
3. Export button: download the impact report as Markdown/JSON.

**DoD**
- Demo flow works end-to-end from the browser on both repos.
- A 3-minute screen recording of the demo flow (insurance for the final review!).

**Fallback if behind:** replace React with a single Streamlit/Plotly page, or just ship the API + Neo4j Browser for graph viewing. The research results matter more than the UI.

---

### WEEK 8 — Final evaluation, report numbers, polish

**Tasks**
1. Freeze code. Run the **final evaluation** on both repos: all methods × test split, ablations, Wilcoxon tests, calibration, cost/time table (Section 11).
2. Run LLM-dependent parts (LLM-only baseline, explanations, semantic linking) **3 times** (cache keyed with a `run_id` for these) and report mean ± std; deterministic parts need one run.
3. Generate figures with matplotlib into `results/figures/`: (a) F2 and P@5 bar chart per method, (b) ablation chart, (c) calibration curve, (d) per-repo comparison.
4. **Manual sanity check:** pick 10 test scenarios per repo, read the top-5 predictions + evidence, and classify each false positive/negative into the error categories of Section 11.7. Write a short error-analysis table.
5. Documentation: README (setup in 5 commands), architecture diagram, `results/` README listing exactly how to reproduce each table.
6. **Buffer** — Weeks 1–7 will slip; this week absorbs it.

**DoD**
- `scripts/run_eval.sh` reproduces the tables in the report from a clean clone (given the cached LLM responses).
- All figures and tables exist; the report's "Results" chapter can be written directly from `results/`.

---

## 9. The impact scoring model (exact definition)

For a seed file **s**, an `as_of` time **T**, and each candidate file **c** in the pooled candidate set:

```
Score(c) = w_struct · S_struct(c) + w_hist · S_hist(c) + w_sem · S_sem(c) + w_link · S_link(c)
Σ w = 1, each S ∈ [0, 1]
```

### 9.1 Signal definitions
- **S_struct** (structural proximity; shortest path `d` over `DEPENDS_ON`/`IMPORTS`, max depth 3):
  - `c` **depends on** `s` (c imports s → *c is a dependent*, usually most impacted): `1.0 / d`
  - `c` **is depended on by** `s` (s imports c): `0.5 / d`
  - `c` is a **test file that imports s**: `1.0`
  - otherwise `0`.
  *(Intuition: if I change a library file, the files that **use** it are at risk more than the files it uses.)*
- **S_hist** = decayed co-change `confidence` from `cochange(s, T)` (Section 8 Week 3), already in [0,1]. Optionally multiply by `min(1, support/5)` to damp pairs seen only once or twice. **Report this choice.**
- **S_sem** = cosine similarity between `s` and `c` embeddings, **min-max normalised over the candidate pool**, only counting items with `created_at < T`.
- **S_link** = maximum `confidence` among inferred/deterministic link paths available at time `T`: `s —VERIFIES/DOCUMENTS→ c`, or both linked to the same `Requirement/Issue` (path `s ← … → c`). Edge `timestamp` must be `< T`.

### 9.2 Default starting weights (before tuning)
`w_struct=0.35, w_hist=0.35, w_sem=0.20, w_link=0.10`

### 9.3 Tuning protocol (on **dev** split only)
- Grid: each weight ∈ {0.0, 0.1, …, 0.6}, constrained to sum to 1 (≈ a few hundred combos — trivial).
- Objective: mean F2 on the dev scenarios (with top-k cutoff `k` also chosen on dev from {3,5,8,10}).
- Freeze `weights.json` and `k`. **Never retune after seeing test results.**
- Ablations just set weights to 0 and renormalise the rest:
  - **No-history:** `w_hist = 0`
  - **Code-only:** `w_sem = 0`, `w_link = 0` (structural + history only)

### 9.4 Confidence
`confidence = IsotonicRegression(Score)` fitted on dev; evaluated on test with Expected Calibration Error (Section 11.5).

---

## 10. LLM design

### 10.1 Where the LLM is used (and where it is NOT)
| Task | LLM? | Model tier |
|---|---|---|
| Parse code structure | ❌ never | — |
| Co-change statistics | ❌ never | — |
| Impact score arithmetic | ❌ never | — |
| Classify a candidate pair (inferred edge) | ✅ | cheap/fast (bulk) |
| Explain an evidence bundle | ✅ | slightly stronger (explain) |
| LLM-only baseline | ✅ | same as bulk model |

### 10.2 Prompt templates (store in `llm/prompts.py`, version them as `PROMPT_V1`, …)

**A. Pair classification (retrieve-then-classify; modelled on P4's four criteria + P3's role/directness lessons):**
```
You are an expert in software traceability. Decide whether the SOURCE artifact
directly {relation} the TARGET artifact.

Criteria (all must hold for "yes"):
1. Coverage: the target addresses the intent of the source.
2. Specificity: the link is specific, not just a generic topical overlap.
3. Terminology: key terms/concepts align.
4. No contradiction: nothing in either text contradicts the link.

SOURCE ({source_type}):
{source_text}

TARGET ({target_type}):
{target_text}

Respond with JSON only, no prose:
{"decision": "yes"|"no", "confidence": <float 0..1>, "justification": "<one sentence>"}
```
`{relation}` ∈ {`implements`, `verifies`, `documents`}. Truncate each text to ~1,200 characters. (P3 found that a single word like *"directly"* measurably improved precision — keep it.)

**B. Explanation (terminal-KG principle):**
```
You are explaining a software change-impact prediction to a developer.
Use ONLY the evidence JSON below. Do not mention any file, commit, or fact that is
not in the JSON. Do not speculate. Write 2–4 sentences. Mention the strongest
evidence first and say how certain the system is (use "confidence_calibrated").

EVIDENCE:
{bundle_json}
```

**C. LLM-only baseline:**
```
A developer will modify the file below in a Python repository. From the list of
repository file paths, return up to 10 paths most likely to ALSO need changes
(tests, dependents, docs). Return JSON only: {"ranked_paths": ["...", ...]}

CHANGED FILE: {seed_path}
CONTENT (truncated):
{seed_content_first_3000_chars}

REPOSITORY FILES:
{file_path_list}
```
Discard any returned path that doesn't exist in the repo (count them as hallucinations — report the rate; it's a nice result!).

### 10.3 Cost and reproducibility rules
- `temperature=0`, JSON mode where supported.
- **Disk cache for every call** (Section 8 Week 6). Never re-pay for a prompt you've already sent.
- Hard budgets: ≤ ~1,500 classification calls/repo; explanations only on demand (top-5 per query) and cached.
- Develop and debug on a tiny sample (e.g., 5 issues) before running the full batch.
- Log tokens/time/USD per stage to `results/cost.csv` (your report's evaluation plan requires a cost table).

### 10.4 Verification gate (implements the terminal-KG principle)
After the explanation is generated:
1. Extract all path-like strings (`[\w./-]+\.\w+`) and 7–40-char hex strings from the text.
2. Every one must appear in `bundle_json`.
3. If any is missing → **reject** the LLM text, use a deterministic template: *"`{candidate}` is predicted affected (confidence X) because: {top evidence items}."*
4. Log the rejection rate — report it.

---

## 11. Evaluation protocol (the part reviewers will grill you on)

### 11.1 What we measure
**Task:** *Given a seed file about to be changed at time T, rank the other files that will be changed along with it.*
**Metrics:** Precision, Recall, F1, **F2 (primary)**, Precision@k, Recall@k, MAP, calibration error, time/tokens/USD.
`F2 = 5·P·R / (4·P + R)` — recall-weighted because missing an impacted file is worse than a reviewable false positive (justified in P2/P3/P4/P10).

### 11.2 Temporal protocol — "single as-of snapshot"
1. Choose a split time **T0** about 60–70% through the repo's history; take the commit at T0 as the **snapshot S**.
2. Build the **structural graph, embeddings, and docs index from snapshot S** (checkout S, then parse). Because S is *older* than every evaluation commit, this contains **no future information** (files created after S are simply unknown to the system).
3. **Scenarios** are commits made *after* T0. For scenario commit **C** at time `t_C`, the system may use only: the snapshot graph/embeddings (older than C), Git history with `ts < t_C` (this *includes* commits between S and C — they are legitimately in the past), and issues/PRs/docs with `created_at < t_C`.
4. `leakage_check.py` enforces this programmatically; failing scenarios are dropped and counted.

> If time allows (optional): re-parse at `parent(C)` for 10 scenarios and show that results match — a nice robustness remark.

### 11.3 Scenario construction (automatic ground truth)
For each repo, over commits after T0:
1. Keep commits that are non-merge, have `2 ≤ files ≤ 10` after applying the same noise filters as the miner, and touch at least one non-test `.py` source file that **exists in snapshot S**.
2. **Seed** = one changed source file (pick with a fixed RNG seed for reproducibility).
3. **Ground-truth set** = the *other* changed files that **exist in snapshot S** (files newly created in C can't be predicted; record how many were excluded).
4. Require ≥ 1 ground-truth file.
5. Sample **~50 scenarios per repo** (spread over time); split **50% dev / 50% test**, stratified so both splits span early and late commits. Save to `results/{repo}_scenarios.json` and commit it.
6. **Manual sanity check:** read 10 scenarios per repo and note how many ground-truth sets look "reasonable" vs noisy. Report this percentage honestly.

### 11.4 Methods compared
| Method | Uses |
|---|---|
| **Static-only** (baseline) | `S_struct` only |
| **Vector-RAG-only** (baseline) | `S_sem` only |
| **LLM-only** (baseline) | Prompt C, no graph/history |
| *History-only* (bonus diagnostic) | `S_hist` only |
| **DevGraph full** | all four signals, tuned weights |
| **Ablation: no-history** | `w_hist=0` |
| **Ablation: code-only** | `w_sem=w_link=0` |

### 11.5 Calibration error (ECE)
Bin predictions by calibrated confidence (10 bins); `ECE = Σ_bins (n_bin/N) · |mean_confidence − hit_rate|` where a *hit* = the predicted candidate is in the ground truth.

### 11.6 Statistics
- Per-scenario F2 (and AP) for each method on the **test** split.
- **Wilcoxon signed-rank test** (`scipy.stats.wilcoxon`) of DevGraph-full vs each baseline and vs each ablation; report p-values and the median improvement. Use α = 0.05; state sample size.
- Report mean ± std for LLM-dependent methods over 3 runs; deterministic methods are exactly reproducible.
- Report results **per repository** and **per repo-size tier**.

### 11.7 Error analysis (10 scenarios/repo, FP and FN)
Categorise each error: **(a)** missing/incorrect structural extraction · **(b)** LLM semantic misjudgment · **(c)** misleading/absent history (coincidental co-change) · **(d)** weight/fusion issue · **(e)** noisy or subjective ground truth. Tabulate counts.

### 11.8 Reproducibility package
Pinned SHAs for all repos, `scenarios.json`, `weights.json`, all prompt templates, cached LLM responses, `requirements.txt` with versions, and `scripts/run_eval.sh`.

### 11.9 What results to expect and how to report them
- It is **plausible** that history-only is already strong and that semantic evidence adds little. Report whatever you find; the ablation table *is* the contribution.
- Never present the automatic ground truth as perfect truth; call it a *proxy validated on a manual sample*.

---

## 12. Minimal specification for API/UI contracts (for Antigravity)

**POST `/impact`** request:
```json
{"repo": "flask", "seed_path": "src/flask/app.py", "as_of": "2024-01-15", "top_k": 10}
```
Response:
```json
{
  "seed": "src/flask/app.py",
  "results": [
    {"path": "tests/test_basic.py", "score": 0.91, "confidence": 0.84,
     "contributions": {"structural": 0.35, "historical": 0.31, "semantic": 0.13, "links": 0.12}}
  ],
  "weights": {"structural": 0.35, "historical": 0.35, "semantic": 0.2, "links": 0.1},
  "disclaimer": "Decision-support only. Human review required."
}
```
Always show the disclaimer in the UI (decision-support framing is part of your report's positioning).

---

## 13. How to save tokens and still learn (Antigravity workflow)

1. **One phase per session.** Paste only: Section 0 rules + the current Week's section + Sections 7/9/10 if relevant. Not the whole file.
2. **Plan → code → test → summarise.** Ask for a 10-line plan first; reject over-engineered plans.
3. **Fixtures before full runs.** Test on 3-file toy repos and on 5 issues before touching a real repo or a paid API.
4. **Ask for diffs, not rewrites.** "Modify only `scoring.py`; do not touch other files."
5. **Tell it what NOT to read:** `data/`, `frontend/node_modules`, `results/`.
6. **Keep a `PROGRESS.md`:** end every session with "update PROGRESS.md with what is done, what is next, known issues". Start the next session by pasting only that file + the next phase.
7. **Learn actively:** after each phase, close the code and write (or say aloud) the Explain-it-back answer. Then open the code and check it. Rotate who explains.
8. **Use free tiers for bulk classification and the local embedding model** — don't spend paid tokens on development.
9. **Cache everything** (LLM, GitHub JSON, embeddings, parsed ASTs).

---

## 14. Risks and the cut list (decide early, not at the deadline)

| Risk | Early warning | Mitigation / cut |
|---|---|---|
| Structural extraction takes too long | End of Week 2 not at DoD | Drop `CALLS`, keep `IMPORTS`/`DEPENDS_ON` (file-level is enough for evaluation) |
| Evaluation not running by end of Week 5 | No metrics table | **Stop everything else**; this is the project |
| LLM free-tier rate limits | Many 429 errors | Lower budgets, use local model (Ollama) for dev, rely on cache |
| Weak/zero improvement from history | Ablation shows nothing | Report honestly; analyse why (error categories). Negative results are valid |
| Second repo not ready | End of Week 5 | Evaluate pilot only + a clearly labelled second repo with fewer scenarios |
| UI takes too long | End of Week 7 | Streamlit page or Neo4j Browser demo |
| Semantic linking too costly | Budget exceeded | Cut `IMPLEMENTS`; keep `VERIFIES` (heuristic + a few LLM calls) |

**Cut order (first to last):** CM1 benchmark → issue/requirement LLM linking → React UI polish → third repo → `CALLS` edges → doc-section linking. **Never cut:** structural graph, evolution miner, scoring, leakage-free evaluation, baselines, ablations, evidence panel.

---

## 15. Viva preparation — questions you must be able to answer

1. **What is the problem?** Change-impact blindness across code/tests/docs because relationships are implicit.
2. **What is novel?** Fusing structural + semantic + historical (Git) evidence, with a temporal leakage-free evaluation and per-edge provenance. Not new: KGs, embeddings, LLMs individually.
3. **Why a knowledge graph and not just a vector DB?** Vector search finds *similar text*; it can't answer "what depends on what" or give inspectable paths.
4. **Why not a GNN?** P5 shows classical models match/beat GNNs on realistic-size software graphs; GNNs hurt explainability and need labelled data and compute.
5. **Why do you need an LLM at all?** Parsing can't tell if an issue is implemented by a function or a doc describes a module; the LLM is used only for semantic classification and explanation.
6. **How do you stop hallucination?** The LLM never creates graph facts; inferred edges are labelled with confidence; explanations pass a verification gate against the evidence bundle (P6's terminal-KG idea).
7. **What is temporal leakage and how do you prevent it?** Using future info to predict the past; enforced via the as-of snapshot, time-filtered history/issues, and a programmatic leakage check.
8. **Why F2?** Missing an impacted artifact costs more than a false alarm (P2/P3/P4/P10).
9. **How do you know your ground truth is good?** It's a proxy (files changed in the same commit); we filtered noisy commits and manually validated a sample; we state it as a limitation.
10. **What if history doesn't help?** Then the ablation reports that; a well-supported negative result is still a valid contribution.
11. **What are the limits?** Python-only, 2–3 repos, approximate call resolution, proxy ground truth, LLM non-determinism (mitigated by temp=0 + cache + repeated runs), no drift detection (future work).
12. **How does it scale?** Mid-size repos (10K–150K LOC); P2 showed retrieval recall collapses on very large projects — future work: module-level clustering.
13. **Why the weighted-sum score?** Interpretable and decomposable — each prediction shows exactly how much each evidence type contributed.
14. **Future work:** drift detection (docs/architecture), multi-language, incremental updates on new commits, dynamic fusion weights, GNN ablation, CI/IDE integration.

---

## 16. Final checklist (tick before the final review)

- [ ] 2 repos indexed (SHA pinned), structural graph + history + vectors present
- [ ] Neo4j graph with provenance on every edge (`confidence`, `method`, `source_commit`, `timestamp`, `is_deterministic`)
- [ ] `cochange()` proven leakage-free by unit test
- [ ] Scenarios frozen (`scenarios.json`), dev/test split, leakage check report (# dropped)
- [ ] Weights tuned on dev only, frozen in `weights.json`
- [ ] Results table: static-only, vector-only, LLM-only, full, no-history, code-only (P@k, R@k, F1, **F2**, MAP) with Wilcoxon p-values
- [ ] Calibration (ECE) + cost/time table
- [ ] Error analysis on manual sample + manual ground-truth sanity percentage
- [ ] Explanation verification-gate tested; rejection rate reported
- [ ] API + minimal UI demo (+ screen recording backup)
- [ ] README with 5-command setup; `scripts/run_eval.sh` reproduces tables
- [ ] Report states clearly: contribution = integration + evaluation; limitations; drift engines = future work
- [ ] Every team member can answer their phase's *Explain-it-back* and the Section 15 questions

---

### Appendix A — Suggested requirements.txt (pin versions after first successful install)
```
fastapi
uvicorn[standard]
pydantic
python-dotenv
neo4j
chromadb
sentence-transformers
tree-sitter
tree-sitter-python
pydriller
GitPython
requests
pyyaml
pandas
numpy
scikit-learn
scipy
joblib
matplotlib
tqdm
pytest
```

### Appendix B — Order of work if everything goes wrong
If you have only **3 weeks** left: Week 2 (structural, file-level `IMPORTS` only) → Week 3 (miner + `cochange`) → Week 5 (scoring + evaluation, structural/history/vector only, no LLM) → then add the LLM-only baseline and a basic explanation. That is still a valid, honest, defensible project.
