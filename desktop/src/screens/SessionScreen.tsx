import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getSession, listShots, getVideoUrl, getCsvUrl } from "@/api/sessions";
import { Session, Shot } from "@/types";
import { KPIStrip } from "@/components/KPIStrip";
import { CourtMap } from "@/components/CourtMap";
import { ShotTable } from "@/components/ShotTable";
import { VideoPlayer } from "@/components/VideoPlayer";
import { ShotTypeChart, SpinTypeChart, SpeedHistogram, QualityHistogram } from "@/components/Charts";
import { StatusBadge } from "@/components/StatusBadge";

type Tab = "overview" | "shots" | "court" | "video";

export function SessionScreen() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<Session | null>(null);
  const [shots, setShots] = useState<Shot[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [activeShot, setActiveShot] = useState<Shot | null>(null);
  const [seekTo, setSeekTo] = useState<number | undefined>();
  const [loading, setLoading] = useState(true);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    if (!id) return;
    try {
      const s = await getSession(id);
      setSession(s);
      if (s.status === "complete") {
        const sh = await listShots(id);
        setShots(sh);
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [id]);

  function handleSelectShot(shot: Shot) {
    setActiveShot(shot);
    setSeekTo(shot.start_time_sec);
    setTab("video");
  }

  function exportCsv() {
    if (!id) return;
    const url = getCsvUrl(id);
    window.electronAPI?.openExternal(url) ?? window.open(url);
  }

  if (loading || !session) {
    return <div className="empty-state"><div className="spinner" /></div>;
  }

  return (
    <div>
      {/* Header */}
      <div className="flex-between" style={{ marginBottom: 18 }}>
        <div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate("/")}
            style={{ marginBottom: 8 }}
          >
            ← All Sessions
          </button>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>{session.filename}</h1>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 3 }}>
            {new Date(session.uploaded_at).toLocaleString()}
            {session.fps ? ` · ${session.fps.toFixed(0)} fps` : ""}
            {session.width ? ` · ${session.width}×${session.height}` : ""}
          </div>
        </div>
        <div className="flex-gap">
          <StatusBadge status={session.status} />
          {session.status === "complete" && (
            <button className="btn btn-secondary btn-sm" onClick={exportCsv}>
              Export CSV
            </button>
          )}
        </div>
      </div>

      {/* Processing / error state */}
      {session.status !== "complete" && (
        <div className="card" style={{ textAlign: "center", padding: 48 }}>
          {session.status === "error" ? (
            <>
              <div style={{ color: "var(--danger)", fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
                Processing failed
              </div>
              <div style={{ color: "var(--muted)", fontSize: 13 }}>{session.error_message}</div>
            </>
          ) : (
            <>
              <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 16px" }} />
              <div style={{ color: "var(--muted)" }}>
                {session.status === "queued" ? "Queued for processing…" : "Processing video…"}
              </div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>
                This may take {session.total_frames ? `~${Math.round(session.total_frames / (session.fps || 60) / 60 * 3)}–${Math.round(session.total_frames / (session.fps || 60) / 60 * 5)} min` : "a few minutes"}
              </div>
            </>
          )}
        </div>
      )}

      {/* Complete state */}
      {session.status === "complete" && (
        <>
          <KPIStrip session={session} shots={shots} />

          {/* Tabs */}
          <div className="tab-bar">
            {(["overview", "video", "court", "shots"] as Tab[]).map((t) => (
              <button
                key={t}
                className={`tab-btn ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {{ overview: "📊 Overview", video: "🎬 Video", court: "🎾 Court Map", shots: "📋 Shots" }[t]}
              </button>
            ))}
          </div>

          {/* Overview tab */}
          {tab === "overview" && (
            <div className="charts-2col">
              <div className="card">
                <div className="card-title">Shot Type</div>
                <ShotTypeChart shots={shots} />
              </div>
              <div className="card">
                <div className="card-title">Spin Type</div>
                <SpinTypeChart shots={shots} />
              </div>
              <div className="card">
                <div className="card-title">Speed Distribution (mph)</div>
                <SpeedHistogram shots={shots} />
              </div>
              <div className="card">
                <div className="card-title">Quality Distribution</div>
                <QualityHistogram shots={shots} />
              </div>
            </div>
          )}

          {/* Video tab */}
          {tab === "video" && (
            <div className="detail-grid">
              <div>
                <VideoPlayer src={getVideoUrl(id!)} seekTo={seekTo} />
                {activeShot && (
                  <div className="card mt-3">
                    <div className="card-title">Active Shot</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px", fontSize: 13 }}>
                      <ShotStat label="Type" value={activeShot.shot_type} />
                      <ShotStat label="Spin" value={activeShot.spin_type} />
                      <ShotStat label="Speed" value={activeShot.speed_mph ? `${activeShot.speed_mph.toFixed(0)} mph` : "—"} />
                      <ShotStat label="RPM" value={activeShot.rpm_estimate ? Math.round(activeShot.rpm_estimate).toString() : "—"} />
                      <ShotStat label="Net" value={activeShot.net_clearance_inches != null ? `${activeShot.net_clearance_inches.toFixed(1)}"` : "—"} />
                      <ShotStat label="Quality" value={activeShot.quality_score != null ? activeShot.quality_score.toFixed(0) : "—"} />
                    </div>
                  </div>
                )}
              </div>
              <div className="card" style={{ padding: 0 }}>
                <div className="flex-between" style={{ padding: "14px 16px" }}>
                  <div className="card-title" style={{ margin: 0 }}>Shots — click to seek</div>
                </div>
                <ShotTable shots={shots} activeShot={activeShot?.shot_id} onSelectShot={handleSelectShot} />
              </div>
            </div>
          )}

          {/* Court map tab */}
          {tab === "court" && (
            <div className="detail-grid">
              <div className="card" style={{ alignSelf: "start" }}>
                <div className="card-title">Bounce Locations</div>
                <CourtMap shots={shots} activeShot={activeShot?.shot_id} onSelectShot={handleSelectShot} />
              </div>
              <div className="card" style={{ padding: 0 }}>
                <div className="flex-between" style={{ padding: "14px 16px" }}>
                  <div className="card-title" style={{ margin: 0 }}>Shots — click to highlight</div>
                </div>
                <ShotTable shots={shots} activeShot={activeShot?.shot_id} onSelectShot={setActiveShot} />
              </div>
            </div>
          )}

          {/* Shots table tab */}
          {tab === "shots" && (
            <div className="card" style={{ padding: 0 }}>
              <div className="flex-between" style={{ padding: "14px 16px" }}>
                <div className="card-title" style={{ margin: 0 }}>All Shots ({shots.length})</div>
                <button className="btn btn-secondary btn-sm" onClick={exportCsv}>Export CSV</button>
              </div>
              <ShotTable shots={shots} activeShot={activeShot?.shot_id} onSelectShot={handleSelectShot} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ShotStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span style={{ color: "var(--muted)", fontSize: 11 }}>{label} </span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}
