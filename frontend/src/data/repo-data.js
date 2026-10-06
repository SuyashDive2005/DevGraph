// Static mock data for the Repositories page. Replace with backend data later;
// keep the same shape and the page will not need to change.

// Helpers keep the tree below readable. flags: impact | drift | frequent | documented | stable
const F = (name, lines, classes, functions, mods, days, flags = [], deps = []) =>
  ({ type: "file", name, lines, classes, functions, mods, days, flags, deps });
const D = (name, children) => ({ type: "folder", name, children });

const withPaths = (n, parent = null) => {
  const path = parent === null ? "" : parent ? `${parent}/${n.name}` : n.name;
  return { ...n, path, children: n.children?.map((c) => withPaths(c, path)) };
};

const tree = withPaths(
  D("DataTrace", [
    D("frontend", [
      D("src", [
        D("components", [
          F("LineageGraph.jsx", 412, 1, 14, 38, 3, ["impact", "frequent"], ["reactflow", "d3"]),
          F("DatasetTable.jsx", 186, 1, 6, 12, 12, ["documented"], ["react-table"]),
          F("Sidebar.jsx", 94, 1, 2, 5, 40, ["stable"]),
        ]),
        D("pages", [
          F("Dashboard.jsx", 220, 1, 8, 17, 6, [], ["axios"]),
          F("Lineage.jsx", 158, 1, 5, 24, 3, ["frequent"], ["axios"]),
        ]),
        F("App.jsx", 64, 1, 3, 6, 52, ["stable"], ["react"]),
        F("main.jsx", 12, 0, 1, 2, 90, ["stable"], ["react-dom"]),
      ]),
      F("package.json", 38, 0, 0, 14, 20),
      F("vite.config.js", 22, 0, 0, 3, 80, ["stable"], ["vite"]),
    ]),
    D("backend", [
      D("routes", [
        F("auth_routes.py", 88, 0, 5, 7, 35, [], ["flask"]),
        F("data_routes.py", 176, 0, 9, 20, 14, ["drift"], ["flask"]),
      ]),
      D("services", [
        F("lineage_service.py", 540, 3, 24, 52, 3, ["impact", "frequent"], ["networkx"]),
        F("ingest_service.py", 310, 2, 15, 31, 9, ["drift"], ["pandas"]),
      ]),
      D("models", [
        F("dataset.py", 120, 2, 8, 25, 21, ["impact", "documented"], ["sqlalchemy"]),
        F("lineage_edge.py", 74, 1, 4, 8, 60, ["stable"], ["sqlalchemy"]),
      ]),
      D("utils", [F("helpers.py", 96, 0, 9, 9, 70, ["stable"])]),
      F("app.py", 58, 0, 3, 11, 52, ["documented"], ["flask"]),
    ]),
    D("tests", [
      F("test_ingest.py", 140, 0, 12, 14, 9, [], ["pytest"]),
      F("test_lineage.py", 205, 0, 18, 19, 4, [], ["pytest"]),
    ]),
    D("docs", [
      F("architecture.md", 210, 0, 0, 7, 70, ["drift"]),
      F("api.md", 160, 0, 0, 9, 45, ["drift"]),
    ]),
    F("README.md", 84, 0, 0, 12, 30, ["documented"]),
    F("requirements.txt", 18, 0, 0, 10, 20),
    F("docker-compose.yml", 42, 0, 0, 6, 55, ["stable"]),
  ])
);

const P = {
  app: "backend/app.py",
  auth: "backend/routes/auth_routes.py",
  data: "backend/routes/data_routes.py",
  lin: "backend/services/lineage_service.py",
  ing: "backend/services/ingest_service.py",
  ds: "backend/models/dataset.py",
  edge: "backend/models/lineage_edge.py",
  help: "backend/utils/helpers.py",
  main: "frontend/src/main.jsx",
  App: "frontend/src/App.jsx",
  dash: "frontend/src/pages/Dashboard.jsx",
  lpage: "frontend/src/pages/Lineage.jsx",
  graph: "frontend/src/components/LineageGraph.jsx",
  table: "frontend/src/components/DatasetTable.jsx",
  side: "frontend/src/components/Sidebar.jsx",
};

// [from, to, kind]  kind: imports | calls | uses
const edges = [
  [P.app, P.auth, "imports"], [P.app, P.data, "imports"],
  [P.data, P.lin, "imports"], [P.data, P.ing, "imports"], [P.data, P.lin, "calls"], [P.data, P.ing, "calls"],
  [P.lin, P.ds, "imports"], [P.lin, P.edge, "imports"], [P.lin, P.help, "imports"],
  [P.lin, P.help, "calls"], [P.lin, P.ds, "uses"], [P.lin, P.edge, "uses"],
  [P.ing, P.ds, "imports"], [P.ing, P.help, "imports"], [P.ing, P.ds, "uses"], [P.ing, P.lin, "calls"],
  [P.auth, P.help, "imports"], [P.auth, P.help, "calls"],
  [P.main, P.App, "imports"], [P.App, P.dash, "imports"], [P.App, P.lpage, "imports"], [P.App, P.side, "imports"],
  [P.dash, P.table, "imports"], [P.lpage, P.graph, "imports"],
  [P.dash, P.data, "calls"], [P.lpage, P.data, "calls"],
  ["tests/test_lineage.py", P.lin, "imports"], ["tests/test_lineage.py", P.edge, "uses"],
  ["tests/test_ingest.py", P.ing, "imports"], ["tests/test_ingest.py", P.ds, "uses"],
  ["docker-compose.yml", P.app, "uses"], ["docker-compose.yml", "requirements.txt", "uses"],
];

const semantic = {
  "": { purpose: "Data lineage and traceability platform.", does: "A Python API ingests datasets and computes lineage; a React UI lets users explore it.", responsibilities: ["Ingest datasets", "Compute lineage", "Visualise data flow"], concepts: ["Data lineage", "Traceability", "Provenance"] },
  frontend: { purpose: "React UI for exploring datasets and lineage.", does: "Renders dashboards, dataset tables and the interactive lineage graph.", responsibilities: ["Views and routing", "Lineage visualisation", "API consumption"], concepts: ["Dashboard", "Lineage graph"] },
  backend: { purpose: "Python API that ingests datasets and computes lineage.", does: "Exposes REST endpoints backed by ingestion and lineage services.", responsibilities: ["HTTP routing", "Business logic", "Persistence models"], concepts: ["REST API", "Dataset", "Lineage"] },
  "backend/services": { purpose: "Core business logic.", does: "Loads datasets and derives the lineage graph between them.", responsibilities: ["Ingestion", "Graph construction", "Traversal queries"], concepts: ["Ingestion", "Upstream / downstream"] },
  "backend/models": { purpose: "Persistent domain models.", does: "Defines datasets and the edges that connect them.", responsibilities: ["Schema definitions", "Relationships"], concepts: ["Dataset", "Lineage edge"] },
  tests: { purpose: "Automated tests for backend services.", does: "Verifies ingestion and lineage behaviour.", responsibilities: ["Unit tests", "Regression coverage"], concepts: ["Test coverage"] },
  docs: { purpose: "Project documentation.", does: "Explains architecture and the public API.", responsibilities: ["Architecture notes", "API reference"], concepts: ["Documentation"] },
  [P.lin]: { purpose: "Builds and queries the data lineage graph.", does: "Traces how datasets flow between sources, transformations and outputs, and answers upstream and downstream queries.", responsibilities: ["Construct lineage edges from ingested datasets", "Resolve upstream and downstream traversal", "Detect cycles and orphaned datasets"], concepts: ["Data lineage", "Upstream / downstream", "Provenance", "Transformation"] },
  [P.ing]: { purpose: "Loads datasets and registers them.", does: "Reads source files, infers schemas and stores dataset records.", responsibilities: ["Parse source files", "Infer schema", "Register datasets"], concepts: ["Ingestion", "Schema inference", "Dataset registry"] },
  [P.data]: { purpose: "HTTP endpoints for datasets and lineage.", does: "Validates requests and delegates to the ingestion and lineage services.", responsibilities: ["Request validation", "Response shaping"], concepts: ["REST API", "Dataset", "Lineage query"] },
  [P.ds]: { purpose: "Core dataset data model.", does: "Represents a dataset with its schema, owner and version.", responsibilities: ["Schema storage", "Versioning"], concepts: ["Dataset", "Schema", "Owner"] },
  [P.graph]: { purpose: "Interactive lineage graph visualisation.", does: "Draws datasets as nodes and highlights downstream impact on selection.", responsibilities: ["Layout and rendering", "Node expansion", "Impact highlighting"], concepts: ["Lineage graph", "Impact highlighting"] },
  [P.lpage]: { purpose: "Lineage exploration page.", does: "Lets users pick a dataset and view its lineage graph.", responsibilities: ["Dataset selection", "Fetch lineage data"], concepts: ["Lineage", "Dataset selection"] },
  [P.app]: { purpose: "Backend entry point.", does: "Creates the app and registers route modules.", responsibilities: ["App setup", "Route registration"], concepts: ["App factory"] },
  "docs/architecture.md": { purpose: "Describes system architecture and data flow.", does: "Documents the ingestion pipeline and service boundaries.", responsibilities: ["Architecture overview"], concepts: ["Architecture", "Data flow"] },
};

const history = {
  [P.lin]: { contributors: [["maya", 31], ["jonas", 14], ["priya", 7]], recent: { title: "Add cycle detection to graph traversal", days: 3, by: "maya" } },
  [P.ing]: { contributors: [["jonas", 22], ["maya", 9]], recent: { title: "Support CSV schema inference", days: 9, by: "jonas" } },
  [P.data]: { contributors: [["priya", 12], ["jonas", 8]], recent: { title: "Add /lineage/<id> endpoint", days: 14, by: "priya" } },
  [P.ds]: { contributors: [["jonas", 18], ["maya", 7]], recent: { title: "Add schema version field", days: 21, by: "jonas" } },
  [P.graph]: { contributors: [["maya", 24], ["priya", 14]], recent: { title: "Highlight downstream impact on select", days: 3, by: "maya" } },
  [P.lpage]: { contributors: [["maya", 15], ["priya", 9]], recent: { title: "Add dataset picker", days: 6, by: "maya" } },
  [P.app]: { contributors: [["jonas", 11]], recent: { title: "Register auth routes", days: 52, by: "jonas" } },
  "docs/architecture.md": { contributors: [["priya", 7]], recent: { title: "Document ingestion pipeline", days: 70, by: "priya" } },
};

export const repositoriesMock = {
  repo: {
    name: "DataTrace",
    url: "github.com/acme/datatrace",
    branch: "main",
    language: "Python · JavaScript",
    status: "complete", // complete | running | failed
    analyzedAt: "12 minutes ago",
  },
  tree,
  edges,
  semantic,
  history,
};