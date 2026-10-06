// Static mock data for the Overview page. Replace with backend responses later;
// keep the same shape and the UI components will not need to change.

export const overviewMock = {
  repo: {
    name: "acme/payments-service",
    url: "github.com/acme/payments-service",
    branch: "main",
    language: "TypeScript",
    commit: "a3f9c21",
    status: "complete", // complete | running | failed
    analyzedAt: "12 minutes ago",
  },

  stats: [
    { key: "files", label: "Files", value: "482" },
    { key: "classes", label: "Classes", value: "64" },
    { key: "functions", label: "Functions", value: "1,326" },
    { key: "deps", label: "Dependencies", value: "87" },
    { key: "loc", label: "Lines of code", value: "58.4k" },
    { key: "tests", label: "Tests", value: "312" },
  ],

  graph: {
    shown: 14,
    total: 1326,
    focus: "n1",
    impacted: ["n1", "n2", "n3", "n5", "n8", "n11"],
    nodes: [
      { id: "n1", label: "PaymentProcessor", type: "class", x: 320, y: 175 },
      { id: "n2", label: "api/checkout", type: "module", x: 110, y: 85 },
      { id: "n3", label: "OrderService", type: "class", x: 120, y: 215 },
      { id: "n4", label: "StripeGateway", type: "class", x: 520, y: 90 },
      { id: "n5", label: "RefundHandler", type: "class", x: 530, y: 235 },
      { id: "n6", label: "validateCard()", type: "function", x: 325, y: 50 },
      { id: "n7", label: "retryCharge()", type: "function", x: 420, y: 320 },
      { id: "n8", label: "ledger/write", type: "module", x: 255, y: 310 },
      { id: "n9", label: "webhooks", type: "module", x: 600, y: 160 },
      { id: "n10", label: "payments.spec", type: "test", x: 60, y: 320 },
      { id: "n11", label: "checkout.spec", type: "test", x: 40, y: 150 },
      { id: "n12", label: "docs/payments.md", type: "doc", x: 215, y: 120 },
      { id: "n13", label: "FraudCheck", type: "class", x: 440, y: 160 },
      { id: "n14", label: "formatMoney()", type: "function", x: 190, y: 40 },
    ],
    edges: [
      ["n2", "n1"], ["n3", "n1"], ["n1", "n4"], ["n1", "n5"], ["n1", "n6"],
      ["n1", "n7"], ["n1", "n8"], ["n4", "n9"], ["n13", "n1"], ["n5", "n8"],
      ["n10", "n1"], ["n11", "n2"], ["n12", "n1"], ["n14", "n2"], ["n7", "n4"],
      ["n3", "n8"],
    ],
  },

  analyses: [
    {
      key: "structural",
      title: "Structural analysis",
      summary: "How the code is organised and connected.",
      rows: [
        ["Modules", "38"],
        ["Circular dependencies", "2"],
        ["Max call depth", "9"],
      ],
    },
    {
      key: "semantic",
      title: "Semantic analysis",
      summary: "What the code is responsible for.",
      rows: [
        ["Domains detected", "6"],
        ["Public APIs", "41"],
        ["Unclear symbols", "17"],
      ],
    },
    {
      key: "historical",
      title: "Historical analysis",
      summary: "How the code has changed over time.",
      rows: [
        ["Commits analysed", "3,204"],
        ["Hotspot files", "9"],
        ["Active contributors", "12"],
      ],
    },
  ],

  insights: [
    {
      key: "impact",
      title: "Impact prediction",
      headline: "Editing PaymentProcessor affects 14 files",
      detail: "Includes 3 modules, 2 classes and 2 test suites downstream.",
      tag: "High impact",
      tone: "warn",
    },
    {
      key: "drift",
      title: "Documentation drift",
      headline: "7 docs no longer match the code",
      detail: "docs/payments.md describes a refund flow that changed in 4 commits.",
      tag: "Needs review",
      tone: "warn",
    },
    {
      key: "trace",
      title: "Traceability",
      headline: "92% of requirements link to code and tests",
      detail: "5 requirements have no covering test.",
      tag: "Healthy",
      tone: "ok",
    },
  ],

  docs: {
    overall: 68,
    status: "7 sections out of date",
    sections: [
      { label: "Public APIs", value: 82 },
      { label: "Modules", value: 71 },
      { label: "Classes", value: 64 },
      { label: "Functions", value: 52 },
    ],
  },

  activity: [
    { id: 1, type: "commit", title: "Retry failed charges with backoff", meta: "maya-r · a3f9c21", time: "2h ago" },
    { id: 2, type: "pr", title: "Merged #418: Split refund handler", meta: "jonas-k", time: "5h ago" },
    { id: 3, type: "drift", title: "Drift found in docs/payments.md", meta: "Detected by analysis", time: "12m ago" },
    { id: 4, type: "docs", title: "Updated webhook setup guide", meta: "priya-s", time: "Yesterday" },
    { id: 5, type: "commit", title: "Add idempotency keys to ledger writes", meta: "jonas-k · 7be01d4", time: "Yesterday" },
    { id: 6, type: "test", title: "12 tests added to checkout.spec", meta: "maya-r", time: "2d ago" },
  ],
};