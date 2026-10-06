import { useState } from "react";
import Overview from "./overview";
import RepositoriesPage from "./repo";
import {
  LayoutDashboard, GitBranch, Network, GitCommitHorizontal, Users, Settings, HelpCircle,
  Menu, Search, Bell, ChevronsLeft, ChevronsRight, ChevronDown, LogOut, User, X,
} from "lucide-react";

const NAV = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Repositories", icon: GitBranch },
  { label: "Dependency Graph", icon: Network },
  { label: "Commits", icon: GitCommitHorizontal },
  { label: "Contributors", icon: Users },
];
const NAV_BOTTOM = [
  { label: "Settings", icon: Settings },
  { label: "Help", icon: HelpCircle },
];

/* ---------- Logo ---------- */
function LogoMark() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" className="fill-blue-600" />
      <path d="M10 22 L16 10 L22 20" className="stroke-white/70" strokeWidth="1.6" fill="none" strokeLinejoin="round" />
      <circle cx="10" cy="22" r="3" className="fill-white" />
      <circle cx="16" cy="10" r="3" className="fill-white" />
      <circle cx="22" cy="20" r="3" className="fill-blue-200" />
    </svg>
  );
}

/* ---------- Sidebar ---------- */
function NavItem({ item, active, collapsed, onClick }) {
  const Icon = item.icon;
  return (
    <button
      onClick={onClick}
      title={collapsed ? item.label : undefined}
      aria-current={active ? "page" : undefined}
      className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
        active ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
      } ${collapsed ? "lg:justify-center" : ""}`}
    >
      <Icon size={18} className={active ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"} />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </button>
  );
}

export function Sidebar({ active, setActive, collapsed, setCollapsed, mobileOpen, setMobileOpen }) {
  const go = (label) => { setActive(label); setMobileOpen(false); };
  return (
    <>
      {mobileOpen && <div className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" onClick={() => setMobileOpen(false)} />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-200 bg-white transition-all duration-200 lg:static ${
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        } ${collapsed ? "w-64 lg:w-[72px]" : "w-64"}`}
      >
        <div className={`flex h-16 items-center border-b border-slate-200 px-4 ${collapsed ? "lg:justify-center" : "justify-between"}`}>
          <div className="flex items-center gap-2.5">
            <LogoMark />
            {!collapsed && <span className="text-lg font-semibold tracking-tight text-slate-900">DevGraph</span>}
          </div>
          <button className="rounded p-1 text-slate-500 hover:bg-slate-100 lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main">
          {NAV.map((i) => (
            <NavItem key={i.label} item={i} collapsed={collapsed} active={active === i.label} onClick={() => go(i.label)} />
          ))}
        </nav>

        <div className="space-y-1 border-t border-slate-200 p-3">
          {NAV_BOTTOM.map((i) => (
            <NavItem key={i.label} item={i} collapsed={collapsed} active={active === i.label} onClick={() => go(i.label)} />
          ))}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-700 lg:flex"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronsRight size={18} className="mx-auto" /> : <><ChevronsLeft size={18} /><span>Collapse</span></>}
          </button>
        </div>
      </aside>
    </>
  );
}

/* ---------- Navbar ---------- */
export function Navbar({ title, onMenu }) {
  const [open, setOpen] = useState(false);
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 sm:px-6">
      <button onClick={onMenu} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Open menu">
        <Menu size={20} />
      </button>
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>

      <div className="relative ml-auto hidden w-80 md:block">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          placeholder="Search repositories, commits, people"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-100"
        />
      </div>

      <button className="relative ml-auto rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 md:ml-0" aria-label="Notifications">
        <Bell size={20} />
        <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-blue-600 ring-2 ring-white" />
      </button>

      <div className="relative">
        <button onClick={() => setOpen(!open)} className="flex items-center gap-2 rounded-lg p-1 pr-2 hover:bg-slate-100" aria-haspopup="menu" aria-expanded={open}>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700">JD</div>
          <ChevronDown size={14} className="hidden text-slate-400 sm:block" />
        </button>
        {open && (
          <div role="menu" className="absolute right-0 mt-2 w-56 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
            <div className="border-b border-slate-100 px-3 py-2">
              <p className="text-sm font-medium text-slate-900">Jane Doe</p>
              <p className="text-xs text-slate-500">jane@devgraph.io</p>
            </div>
            <button role="menuitem" className="flex w-full items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"><User size={15} />Profile</button>
            <button role="menuitem" className="flex w-full items-center gap-2 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"><Settings size={15} />Settings</button>
            <button role="menuitem" className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"><LogOut size={15} />Log out</button>
          </div>
        )}
      </div>
    </header>
  );
}

/* ---------- Layout (wrap each page in this) ---------- */
export default function AppLayout({ children }) {
  const [active, setActive] = useState("Overview");
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800">
      <Sidebar active={active} setActive={setActive} collapsed={collapsed} setCollapsed={setCollapsed} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar title={active} onMenu={() => setMobileOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          {children ?? (
            active === "Overview" ? <Overview /> :
            active === "Repositories" ? <RepositoriesPage /> :
            <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-500">
              {active} page content goes here
            </div>
          )}
        </main>
      </div>
    </div>
  );
}