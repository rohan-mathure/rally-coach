import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listSessions, uploadSessionFile } from "@/api/sessions";
import { Session } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";

export function HomeScreen() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [uploadMsg, setUploadMsg] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function load() {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      /* server may still be starting */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    pollRef.current = setInterval(load, 8000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  async function handleFile(file: File) {
    if (!file.type.startsWith("video/")) {
      setUploadMsg("Please select a video file.");
      return;
    }
    setUploading(true);
    setUploadPct(0);
    setUploadMsg(`Uploading ${file.name}…`);
    try {
      const { session_id } = await uploadSessionFile(file, setUploadPct);
      setUploadMsg("Upload complete — processing…");
      await load();
      navigate(`/session/${session_id}`);
    } catch (err: any) {
      setUploadMsg(`Upload failed: ${err?.message ?? "unknown error"}`);
    } finally {
      setUploading(false);
    }
  }

  async function openNativePicker() {
    if (!window.electronAPI) return fileInputRef.current?.click();
    const path = await window.electronAPI.openFileDialog();
    if (!path) return;
    // Convert native path to File via fetch (blob URL approach)
    try {
      setUploading(true);
      setUploadPct(0);
      setUploadMsg("Reading file…");
      const res = await fetch(`file://${path}`);
      const blob = await res.blob();
      const name = path.split(/[/\\]/).pop() ?? "video.mp4";
      const file = new File([blob], name, { type: blob.type || "video/mp4" });
      await handleFile(file);
    } catch (err: any) {
      setUploadMsg(`Failed to read file: ${err?.message}`);
      setUploading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <div style={{ maxWidth: 820, margin: "0 auto" }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Sessions</h1>

      {/* Upload zone */}
      <div
        className={`drop-zone ${dragging ? "over" : ""}`}
        onClick={openNativePicker}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{ marginBottom: 24 }}
      >
        <div className="icon">🎾</div>
        <div style={{ fontWeight: 600 }}>Drop a video or click to browse</div>
        <div className="hint">MP4 · MOV · AVI · 60fps recommended</div>
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          style={{ display: "none" }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
      </div>

      {/* Upload progress */}
      {(uploading || uploadMsg) && (
        <div className="card mt-3" style={{ marginBottom: 18 }}>
          <div className="flex-between" style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--muted)" }}>{uploadMsg}</span>
            {uploading && <div className="spinner" />}
          </div>
          {uploading && (
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${uploadPct}%` }} />
            </div>
          )}
        </div>
      )}

      {/* Session list */}
      {loading ? (
        <div className="empty-state"><div className="spinner" /></div>
      ) : sessions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📹</div>
          <div>No sessions yet — upload a video to get started</div>
        </div>
      ) : (
        <div>
          {/* Table header */}
          <div
            className="session-row"
            style={{ cursor: "default", background: "transparent", border: "none", padding: "4px 16px", marginBottom: 4 }}
          >
            <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.6px" }}>File</span>
            <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.6px" }}>Status</span>
            <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.6px" }}>Shots</span>
            <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.6px" }}>Avg Speed</span>
            <span style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.6px" }}>Avg Quality</span>
            <span />
          </div>

          <div className="session-list">
            {sessions.map((s) => (
              <div
                key={s.session_id}
                className="session-row"
                onClick={() => s.status === "complete" && navigate(`/session/${s.session_id}`)}
                style={{ opacity: s.status === "error" ? 0.6 : 1 }}
              >
                <div>
                  <div className="session-name">{s.filename}</div>
                  <div className="session-date">{new Date(s.uploaded_at).toLocaleString()}</div>
                </div>
                <StatusBadge status={s.status} />
                <span>{s.total_shots || "—"}</span>
                <span>{s.avg_speed_mph ? `${s.avg_speed_mph} mph` : "—"}</span>
                <span>{s.avg_quality_score ? s.avg_quality_score.toFixed(0) : "—"}</span>
                <span>
                  {s.status === "complete" ? (
                    <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); navigate(`/session/${s.session_id}`); }}>
                      View →
                    </button>
                  ) : s.status === "processing" || s.status === "queued" ? (
                    <div className="spinner" style={{ width: 16, height: 16 }} />
                  ) : s.status === "error" ? (
                    <span style={{ fontSize: 11, color: "var(--danger)" }} title={s.error_message}>Error</span>
                  ) : null}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
