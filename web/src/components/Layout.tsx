import { useEffect, useState } from "react";
import { NavLink, Outlet, Link } from "react-router-dom";
import { api } from "../api/client";

const navigation = [
  ["desk", "Desk"],
  ["intake", "Intake"],
  ["expiry", "Expiry"],
  ["basis", "Basis"],
  ["alerts", "Alerts"],
  ["munimji", "Munimji"],
  ["lab", "Strategy lab"],
  ["verdict", "Verdict"],
];

export function Layout() {
  const [backendConnected, setBackendConnected] = useState(false);

  useEffect(() => {
    let active = true;
    const checkBackend = () => {
      api.get("/health")
        .then(() => { if (active) setBackendConnected(true); })
        .catch(() => { if (active) setBackendConnected(false); });
    };
    checkBackend();
    const interval = window.setInterval(checkBackend, 15000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/desk">
          <span className="brand-mark">G</span>
          <span><strong>Goldlens</strong><small>Commodity research</small></span>
        </Link>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-name">MCX GOLD · RESEARCH</div>
        <div className="dataset-state"><span /> SYNTHETIC DATASET</div>
        <nav className="side-nav" aria-label="Workspace navigation">
          {navigation.map(([path, label]) => (
            <NavLink
              className={({ isActive }) => `side-link${isActive ? " active" : ""}`}
              key={path}
              to={`/${path}`}
            >
              <span className="side-glyph">{label.slice(0, 1)}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="manifest">
          <div className="workspace-label">RUN MANIFEST</div>
          <code>Awaiting dataset</code>
          <span>Policy: turnover or open</span>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">Goldlens <span>/</span> <strong>Research workspace</strong></div>
          <div className={`top-status${backendConnected ? "" : " offline"}`}><span className="status-dot" /> {backendConnected ? "Backend connected" : "Backend offline"}</div>
        </header>
        <div className="page-content"><Outlet /></div>
      </main>
    </div>
  );
}
