import { useCallback, useMemo, useState } from "react";
import {
  Folder, FolderOpen, FileCode2, FileText, ChevronRight, Search, Link2, GitBranch, Code2,
  CheckCircle2, Loader2, XCircle, Zap, FileWarning, Flame, BookCheck, ShieldCheck, Package, ArrowDownUp,
} from "lucide-react";
import { repositoriesMock } from "../data/repo-data";

/* ---------- Config & helpers ---------- */
const IND = {
  impact: { label: "High Impact", Icon: Zap, cls: "bg-red-50 text-red-700 ring-red-200", icon: "text-red-500", why: "Many components depend on this, so changes ripple widely." },
  drift: { label: "Documentation Drift", Icon: FileWarning, cls: "bg-amber-50 text-amber-700 ring-amber-200", icon: "text-amber-500", why: "Documentation no longer matches the current implementation." },
  frequent: { label: "Frequently Changed", Icon: Flame, cls: "bg-sky-50 text-sky-700 ring-sky-200", icon: "text-sky-500", why: "Modified far more often than the rest of the repository." },
  documented: { label: "Well Documented", Icon: BookCheck, cls: "bg-emerald-50 text-emerald-700 ring-emerald-200", icon: "text-emerald-500", why: "Most public symbols are covered by docs and docstrings." },
  stable: { label: "Stable", Icon: ShieldCheck, cls: "bg-slate-100 text-slate-600 ring-slate-200", icon: "text-slate-400", why: "Rarely changes and has seen few recent edits." },
};
const FILE_TYPE = { py: "Python", js: "JavaScript", jsx: "React (JSX)", json: "JSON", md: "Markdown", txt: "Text", yml: "YAML" };
const CODE = ["py", "js", "jsx"];
const ext = (n) => n.split(".").pop();
const isCode = (n) => CODE.includes(ext(n));
const ago = (d) => (d < 1 ? "today" : d === 1 ? "yesterday" : d < 14 ? `${d} days ago` : d < 60 ? `${Math.round(d / 7)} weeks ago` : `${Math.round(d / 30)} months ago`);
const freq = (m) => (m >= 40 ? "High" : m >= 15 ? "Moderate" : "Low");
const uniq = (a) => [...new Set(a)];

function buildIndex(tree, edges) {
  const byPath = {}, stats = {}, files = {}, deg = {};
  edges.forEach(([a, b]) => { deg[a] = (deg[a] || 0) + 1; deg[b] = (deg[b] || 0) + 1; });
  const walk = (n) => {
    byPath[n.path] = n;
    if (n.type === "file") {
      stats[n.path] = { files: 1, folders: 0, classes: n.classes, functions: n.functions, lines: n.lines, mods: n.mods, deg: deg[n.path] || 0 };
      files[n.path] = [n.path];
      return;
    }
    const s = { files: 0, folders: 0, classes: 0, functions: 0, lines: 0, mods: 0, deg: 0 };
    files[n.path] = [];
    n.children.forEach((c) => {
      walk(c);
      Object.keys(s).forEach((k) => { s[k] += stats[c.path][k]; });
      if (c.type === "folder") s.folders += 1;
      files[n.path].push(...files[c.path]);
    });
    stats[n.path] = s;
  };
  walk(tree);
  return { byPath, stats, files };
}

// Relationships crossing the boundary of a set of files (one file or a whole folder).
function relate(paths, edges) {
  const S = new Set(paths);
  const out = (k) => uniq(edges.filter((e) => S.has(e[0]) && !S.has(e[1]) && (!k || e[2] === k)).map((e) => e[1]));
  const inc = (k) => uniq(edges.filter((e) => S.has(e[1]) && !S.has(e[0]) && (!k || e[2] === k)).map((e) => e[0]));
  return { imports: out("imports"), calls: out("calls"), calledBy: inc("calls"), uses: out("uses"), usedBy: inc(), deps: out() };
}

function prune(n, q, filter, cmp, root = false) {
  const hit = !q || n.name.toLowerCase().includes(q);
  if (n.type === "file") return filter !== "folders" && hit ? n : null;
  const kids = n.children.map((c) => prune(c, q, filter, cmp)).filter(Boolean).sort(cmp);
  if (root || (q ? hit || kids.length : filter !== "files" || kids.length)) return { ...n, children: kids };
  return null;
}

/* ---------- Small UI pieces ---------- */
const STATUS = {
  complete: ["Analysis complete", "bg-emerald-50 text-emerald-700 ring-emerald-200", CheckCircle2],
  running: ["Analysing", "bg-blue-50 text-blue-700 ring-blue-200", Loader2],
  failed: ["Analysis failed", "bg-red-50 text-red-700 ring-red-200", XCircle],
};
function StatusBadge({ status }) {
  const [label, cls, Icon] = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${cls}`}>
      <Icon size={13} className={status === "running" ? "animate-spin" : ""} />{label}
    </span>
  );
}

function IndicatorBadge({ k }) {
  const { label, Icon, cls } = IND[k];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${cls}`}>
      <Icon size={11} />{label}
    </span>
  );
}

const TAG = { Structural: "bg-blue-50 text-blue-700", Semantic: "bg-teal-50 text-teal-700", Historical: "bg-orange-50 text-orange-700", DevGraph: "bg-slate-100 text-slate-600" };
function Section({ tag, title, children }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white">
      <header className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        <span className={`rounded-md px-2 py-0.5 text-[11px] font-medium ${TAG[tag]}`}>{tag} analysis</span>
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

function PathButton({ path, jump }) {
  return (
    <button onClick={() => jump(path)} className="block w-full truncate rounded px-1.5 py-1 text-left font-mono text-xs text-slate-600 hover:bg-blue-50 hover:text-blue-700" title={path}>
      {path}
    </button>
  );
}

function RelGroup({ label, items, external = [], jump }) {
  const n = items.length + external.length;
  return (
    <div className="min-w-0 rounded-lg border border-slate-200 p-3">
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-slate-700">{label}</span>
        <span className="tabular-nums text-slate-400">{n}</span>
      </div>
      {n === 0 && <p className="px-1.5 text-xs text-slate-400">None</p>}
      {items.map((p) => <PathButton key={p} path={p} jump={jump} />)}
      <div className="flex flex-wrap gap-1.5 px-1.5">
        {external.map((e) => (
          <span key={e} className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600"><Package size={10} />{e}</span>
        ))}
      </div>
    </div>
  );
}

/* ---------- Header & toolbar ---------- */
function RepoHeader({ repo }) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{repo.name}</h1>
        <StatusBadge status={repo.status} />
      </div>
      <p className="mt-1.5 flex items-center gap-1.5 font-mono text-sm text-slate-500"><Link2 size={14} />{repo.url}</p>
      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-slate-600">
        <span className="flex items-center gap-1.5"><GitBranch size={14} className="text-slate-400" />{repo.branch}</span>
        <span className="flex items-center gap-1.5"><Code2 size={14} className="text-slate-400" />{repo.language}</span>
        <span className="text-slate-500">Last analysed {repo.analyzedAt}</span>
      </div>
    </div>
  );
}

function Toolbar({ q, setQ, filter, setFilter, sort, setSort, total, shown }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 md:flex-row md:items-center">
      <div className="relative flex-1">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search files and folders"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100" />
      </div>
      <div className="flex rounded-lg border border-slate-200 p-0.5 text-sm" role="group" aria-label="Filter">
        {[["all", "All"], ["files", "Files"], ["folders", "Folders"]].map(([v, l]) => (
          <button key={v} onClick={() => setFilter(v)} aria-pressed={filter === v}
            className={`rounded-md px-3 py-1.5 font-medium ${filter === v ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}>{l}</button>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <ArrowDownUp size={15} className="text-slate-400" />
        <select value={sort} onChange={(e) => setSort(e.target.value)} className="rounded-lg border border-slate-200 bg-white py-2 pl-2 pr-7 text-sm focus:border-blue-500 focus:outline-none">
          <option value="name">Name</option><option value="lines">Lines of code</option>
          <option value="changes">Most changed</option><option value="connected">Most connected</option>
        </select>
      </label>
      <p className="whitespace-nowrap text-xs text-slate-500 md:pl-1">
        {q ? <>{shown} matches · </> : null}{total.files} files · {total.folders} folders
      </p>
    </div>
  );
}

/* ---------- Tree ---------- */
function TreeNode({ node, depth, ctx }) {
  const { q, expanded, selected, pick, flagsOf } = ctx;
  const folder = node.type === "folder";
  const open = folder && (q || expanded.has(node.path));
  const flags = flagsOf(node).filter((k) => !folder || k === "impact" || k === "drift").slice(0, 3);
  const Icon = folder ? (open ? FolderOpen : Folder) : isCode(node.name) ? FileCode2 : FileText;
  const sel = selected === node.path;
  return (
    <li role="none">
      <button role="treeitem" aria-selected={sel} aria-expanded={folder ? !!open : undefined} onClick={() => pick(node)}
        style={{ paddingLeft: depth * 16 + 8 }}
        className={`flex w-full items-center gap-1.5 rounded-md py-1.5 pr-2 text-left text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${sel ? "bg-blue-50 text-blue-800" : "text-slate-700 hover:bg-slate-50"}`}>
        <ChevronRight size={14} className={`shrink-0 text-slate-400 transition-transform ${open ? "rotate-90" : ""} ${folder ? "" : "invisible"}`} />
        <Icon size={15} className={`shrink-0 ${folder ? "text-slate-500" : "text-slate-400"}`} />
        <span className="truncate">{node.name}{folder && depth > 0 ? "/" : ""}</span>
        <span className="ml-auto flex shrink-0 items-center gap-1.5">
          {flags.map((k) => { const { Icon: I, icon, label } = IND[k]; return <span key={k} title={label}><I size={12} className={icon} /></span>; })}
          {!folder && <span className="w-9 text-right text-[11px] tabular-nums text-slate-400">{node.lines}</span>}
        </span>
      </button>
      {open && node.children.length > 0 && (
        <ul role="group">{node.children.map((c) => <TreeNode key={c.path} node={c} depth={depth + 1} ctx={ctx} />)}</ul>
      )}
    </li>
  );
}

/* ---------- Detail panel ---------- */
function Stat({ label, value }) {
  return (
    <div className="px-4 py-3">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">{value}</dd>
    </div>
  );
}
const Field = ({ label, children }) => (
  <div><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-0.5 text-sm font-medium text-slate-900">{children}</dd></div>
);

function Detail({ node, idx, data, jump, flagsOf }) {
  const folder = node.type === "folder";
  const paths = idx.files[node.path];
  const files = paths.map((p) => idx.byPath[p]);
  const s = idx.stats[node.path];
  const r = relate(paths, data.edges);
  const external = uniq(files.flatMap((f) => f.deps || []));
  const depCount = r.deps.length + external.length;
  const sem = data.semantic[node.path];
  const code = folder || isCode(node.name);
  const num = (v) => (code ? v : "—");

  const hist = paths.map((p) => data.history[p]).filter(Boolean);
  const contrib = Object.entries(hist.flatMap((h) => h.contributors).reduce((a, [n, c]) => ({ ...a, [n]: (a[n] || 0) + c }), {})).sort((a, b) => b[1] - a[1]);
  const recent = hist.map((h) => h.recent).sort((a, b) => a.days - b.days)[0];
  const lastDays = Math.min(...files.map((f) => f.days));
  const hotspot = [...files].sort((a, b) => b.mods - a.mods)[0];
  const important = [...files].sort((a, b) => idx.stats[b.path].deg - idx.stats[a.path].deg).slice(0, 4);
  const flags = flagsOf(node);
  const crumbs = ["DataTrace", ...node.path.split("/").filter(Boolean)];
  const Icon = folder ? FolderOpen : isCode(node.name) ? FileCode2 : FileText;

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><Icon size={20} /></div>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-lg font-semibold text-slate-900">{folder ? (node.path ? node.name + "/" : "DataTrace/") : node.name}</h2>
            <p className="truncate font-mono text-xs text-slate-500">{crumbs.join(" / ")}</p>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">{folder ? "Folder" : FILE_TYPE[ext(node.name)] || "File"}</span>
              {flags.map((k) => <IndicatorBadge key={k} k={k} />)}
            </div>
          </div>
        </div>
        <dl className="-mx-1 mt-4 grid grid-cols-2 divide-x divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200 sm:grid-cols-5 sm:divide-y-0">
          {folder ? (<>
            <Stat label="Files" value={s.files} /><Stat label="Classes" value={s.classes} /><Stat label="Functions" value={s.functions} />
            <Stat label="Dependencies" value={depCount} /><Stat label="Lines" value={s.lines.toLocaleString()} />
          </>) : (<>
            <Stat label="Lines" value={s.lines} /><Stat label="Classes" value={num(s.classes)} /><Stat label="Functions" value={num(s.functions)} />
            <Stat label="Dependencies" value={depCount} /><Stat label="Used by" value={r.usedBy.length} />
          </>)}
        </dl>
        {folder && important.length > 0 && (
          <div className="mt-4">
            <p className="mb-1.5 text-xs font-medium text-slate-500">Most connected components</p>
            <ul className="space-y-0.5">
              {important.map((f) => (
                <li key={f.path} className="flex items-center gap-2">
                  <div className="min-w-0 flex-1"><PathButton path={f.path} jump={jump} /></div>
                  <span className="text-[11px] tabular-nums text-slate-400">{idx.stats[f.path].deg} links</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <Section tag="Structural" title="Relationships">
        <div className="grid gap-3 sm:grid-cols-2">
          <RelGroup label="Imports" items={r.imports} jump={jump} />
          <RelGroup label="Calls" items={r.calls} jump={jump} />
          <RelGroup label="Called by" items={r.calledBy} jump={jump} />
          <RelGroup label="Uses" items={r.uses} jump={jump} />
          <RelGroup label="Used by" items={r.usedBy} jump={jump} />
          <RelGroup label="Dependencies" items={r.deps} external={external} jump={jump} />
        </div>
      </Section>

      <Section tag="Semantic" title="Purpose & meaning">
        {sem ? (
          <div className="space-y-4">
            <div><p className="text-sm font-medium text-slate-900">{sem.purpose}</p><p className="mt-1 text-sm leading-relaxed text-slate-600">{sem.does}</p></div>
            <div>
              <p className="mb-1.5 text-xs font-medium text-slate-500">Responsibilities</p>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 marker:text-slate-300">{sem.responsibilities.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
            <div>
              <p className="mb-1.5 text-xs font-medium text-slate-500">Business / semantic concepts</p>
              <div className="flex flex-wrap gap-1.5">{sem.concepts.map((c) => <span key={c} className="rounded-full bg-teal-50 px-2.5 py-1 text-xs text-teal-700">{c}</span>)}</div>
            </div>
          </div>
        ) : <p className="text-sm text-slate-400">No semantic summary is available for this item in the mock data.</p>}
      </Section>

      <Section tag="Historical" title="Change history">
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field label="Modifications">{s.mods}</Field>
          <Field label="Last modified">{ago(lastDays)}</Field>
          <Field label="Change frequency">{freq(folder ? hotspot.mods : node.mods)}</Field>
          {folder ? <Field label="Hotspot"><button onClick={() => jump(hotspot.path)} className="truncate text-blue-700 hover:underline">{hotspot.name}</button></Field> : <Field label="Contributors">{contrib.length || "—"}</Field>}
        </dl>
        {contrib.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {contrib.map(([n, c]) => (
              <span key={n} className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 py-0.5 pl-0.5 pr-2.5 text-xs text-slate-600">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold uppercase text-slate-600">{n[0]}</span>{n} · {c}
              </span>
            ))}
          </div>
        )}
        <div className="mt-4 rounded-lg bg-slate-50 px-3.5 py-3">
          <p className="text-xs font-medium text-slate-500">Recent important change</p>
          {recent ? <p className="mt-0.5 text-sm text-slate-800">{recent.title} <span className="text-slate-400">· {recent.by}, {ago(recent.days)}</span></p>
            : <p className="mt-0.5 text-sm text-slate-400">No notable change recorded.</p>}
        </div>
      </Section>

      <Section tag="DevGraph" title="Indicators">
        {flags.length === 0 ? <p className="text-sm text-slate-400">No indicators for this item.</p> : (
          <ul className="space-y-3">
            {flags.map((k) => {
              const flagged = folder ? files.filter((f) => f.flags.includes(k)) : [];
              return (
                <li key={k} className="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-3">
                  <div className="sm:w-48 sm:shrink-0"><IndicatorBadge k={k} /></div>
                  <div className="min-w-0 text-sm text-slate-600">
                    {folder ? (<><span className="text-slate-500">{flagged.length} {flagged.length === 1 ? "file" : "files"}: </span>
                      {flagged.map((f, i) => <span key={f.path}><button onClick={() => jump(f.path)} className="text-blue-700 hover:underline">{f.name}</button>{i < flagged.length - 1 ? ", " : ""}</span>)}</>) : IND[k].why}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Section>
    </div>
  );
}

/* ---------- Page ---------- */
export default function RepositoriesPage({ data = repositoriesMock }) {
  const idx = useMemo(() => buildIndex(data.tree, data.edges), [data]);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("name");
  const [selected, setSelected] = useState("backend/services/lineage_service.py");
  const [expanded, setExpanded] = useState(() => new Set(["", "backend", "backend/services"]));

  const flagsOf = (n) => {
    const present = new Set(idx.files[n.path].flatMap((p) => idx.byPath[p].flags));
    return Object.keys(IND).filter((k) => present.has(k));
  };
  const cmp = useCallback((a, b) => {
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    const A = idx.stats[a.path], B = idx.stats[b.path];
    const v = { name: 0, lines: B.lines - A.lines, changes: B.mods - A.mods, connected: B.deg - A.deg }[sort];
    return v || a.name.localeCompare(b.name);
  }, [idx, sort]);
  const query = q.trim().toLowerCase();
  const view = useMemo(() => prune(data.tree, query, filter, cmp, true), [data.tree, query, filter, cmp]);
  const total = idx.stats[""];
  const shown = view ? Object.values(idx.byPath).filter((n) => n.path && n.name.toLowerCase().includes(query)).length : 0;

  const pick = (node) => {
    setSelected(node.path);
    if (node.type === "folder") setExpanded((s) => { const n = new Set(s); n.has(node.path) ? n.delete(node.path) : n.add(node.path); return n; });
  };
  const jump = (path) => {
    setSelected(path);
    const parts = path.split("/");
    setExpanded((s) => { const n = new Set(s); n.add(""); parts.slice(0, -1).forEach((_, i) => n.add(parts.slice(0, i + 1).join("/"))); return n; });
  };
  const ctx = { q: query, expanded, selected, pick, flagsOf };
  const node = idx.byPath[selected] || data.tree;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <RepoHeader repo={data.repo} />
      <Toolbar q={q} setQ={setQ} filter={filter} setFilter={setFilter} sort={sort} setSort={setSort} total={{ files: total.files, folders: total.folders }} shown={shown} />
      <div className="grid items-start gap-5 lg:grid-cols-[380px_minmax(0,1fr)]">
        <section className="rounded-xl border border-slate-200 bg-white lg:sticky lg:top-0">
          <header className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <h2 className="text-sm font-semibold text-slate-900">Repository structure</h2>
            <span className="text-[11px] text-slate-400">lines</span>
          </header>
          <ul role="tree" className="max-h-[calc(100vh-17rem)] min-h-[280px] overflow-y-auto p-2">
            {view ? <TreeNode node={{ ...view, name: "DataTrace" }} depth={0} ctx={{ ...ctx, expanded: new Set([...expanded, ""]) }} /> : null}
            {view && view.children.length === 0 && <li className="px-3 py-6 text-center text-sm text-slate-400">Nothing matches “{q}”.</li>}
          </ul>
        </section>
        <Detail node={node} idx={idx} data={data} jump={jump} flagsOf={flagsOf} />
      </div>
    </div>
  );
}