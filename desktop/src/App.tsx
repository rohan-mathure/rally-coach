import { useEffect, useState } from "react";
import { HashRouter, Routes, Route, NavLink } from "react-router-dom";
import { setBaseURL } from "@/api/client";
import { HomeScreen } from "@/screens/HomeScreen";
import { SessionScreen } from "@/screens/SessionScreen";

function ServerBootstrap({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!window.electronAPI) {
      // Browser dev mode — assume default port
      setBaseURL(8000);
      setReady(true);
      return;
    }

    // Check if already got port (e.g., hot-reload)
    window.electronAPI.getServerPort().then((port) => {
      if (port) { setBaseURL(port); setReady(true); return; }
      // Otherwise wait for server-ready event
      window.electronAPI.onServerReady((port) => {
        setBaseURL(port);
        setReady(true);
      });
    });

    // Timeout guard
    const t = setTimeout(() => {
      if (!ready) setError("Server took too long to start. Check that Python and all dependencies are installed.");
    }, 40_000);
    return () => clearTimeout(t);
  }, []);

  if (error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", gap: 16 }}>
        <div style={{ fontSize: 32 }}>⚠️</div>
        <div style={{ color: "var(--danger)", fontWeight: 600 }}>Startup Error</div>
        <div style={{ color: "var(--muted)", fontSize: 13, maxWidth: 400, textAlign: "center" }}>{error}</div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100vh", gap: 16 }}>
        <div style={{ fontSize: 32 }}>🎾</div>
        <div style={{ fontWeight: 600, fontSize: 16 }}>Starting Rally Coach…</div>
        <div className="spinner" style={{ width: 28, height: 28 }} />
        <div style={{ color: "var(--muted)", fontSize: 12 }}>Starting analysis server</div>
      </div>
    );
  }

  return <>{children}</>;
}

export function App() {
  return (
    <HashRouter>
      <div className="app-shell">
        {/* Titlebar */}
        <div className="titlebar">
          <span className="logo">Rally<span>Coach</span></span>
          <div className="titlebar-actions">
            <NavLink to="/" className="btn btn-secondary btn-sm" style={{ textDecoration: "none" }}>
              Sessions
            </NavLink>
          </div>
        </div>

        {/* Main */}
        <div className="main-content">
          <ServerBootstrap>
            <Routes>
              <Route path="/" element={<HomeScreen />} />
              <Route path="/session/:id" element={<SessionScreen />} />
            </Routes>
          </ServerBootstrap>
        </div>
      </div>
    </HashRouter>
  );
}
