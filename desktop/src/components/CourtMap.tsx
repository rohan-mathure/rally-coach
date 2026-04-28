import { Shot, ShotType } from "@/types";
import { useMemo, useState } from "react";

const W = 280;
const H = 450;
const PAD = 24;
const COURT_W_FT = 27;
const COURT_L_FT = 78;
const SX = (W - PAD * 2) / COURT_W_FT;
const SY = (H - PAD * 2) / COURT_L_FT;

function px(cx: number, cy: number): [number, number] {
  return [PAD + (cx + COURT_W_FT / 2) * SX, PAD + cy * SY];
}

const COURT_LINES: [[number, number], [number, number]][] = [
  [[-13.5, 0], [13.5, 0]],    // near baseline
  [[-13.5, 78], [13.5, 78]],  // far baseline
  [[-13.5, 0], [-13.5, 78]],  // left sideline
  [[13.5, 0], [13.5, 78]],    // right sideline
  [[-13.5, 39], [13.5, 39]],  // net
  [[-13.5, 57], [13.5, 57]],  // near service line
  [[-13.5, 21], [13.5, 21]],  // far service line
  [[0, 21], [0, 57]],         // center service line
];

const FILTER_OPTIONS: { key: "all" | ShotType; label: string }[] = [
  { key: "all", label: "All" },
  { key: "forehand", label: "FH" },
  { key: "backhand", label: "BH" },
  { key: "volley", label: "VOL" },
  { key: "overhead", label: "OH" },
];

interface Props {
  shots: Shot[];
  onSelectShot?: (shot: Shot) => void;
  activeShot?: string;
}

export function CourtMap({ shots, onSelectShot, activeShot }: Props) {
  const [filter, setFilter] = useState<"all" | ShotType>("all");
  const [hovered, setHovered] = useState<string | null>(null);

  const visible = useMemo(
    () => shots.filter((s) => filter === "all" || s.shot_type === filter),
    [shots, filter]
  );

  const dots = useMemo(
    () =>
      visible
        .filter((s) => s.bounce_court_x != null && s.bounce_court_y != null)
        .map((s) => {
          const [x, y] = px(s.bounce_court_x!, s.bounce_court_y!);
          const r = 4 + (s.quality_score ?? 0) / 20;
          const isClose = s.is_close_call === 1 || s.is_close_call === true;
          const isIn = s.is_in === 1 || s.is_in === true;
          const fill = isClose ? "#f59e0b" : isIn ? "#4ade80" : "#f87171";
          return { s, x, y, r, fill };
        }),
    [visible]
  );

  const hoveredShot = hovered ? shots.find((s) => s.shot_id === hovered) : null;

  return (
    <div>
      {/* Filter bar */}
      <div className="flex-gap" style={{ marginBottom: 12 }}>
        {FILTER_OPTIONS.map(({ key, label }) => (
          <button
            key={key}
            className={`btn btn-secondary btn-sm ${filter === key ? "active" : ""}`}
            style={filter === key ? { borderColor: "var(--accent)", color: "var(--accent)" } : {}}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* SVG court */}
      <svg width={W} height={H} style={{ display: "block", margin: "0 auto" }}>
        {/* Court background */}
        <rect x={PAD} y={PAD} width={W - PAD * 2} height={H - PAD * 2} fill="#1e2a3a" rx={2} />

        {/* Court lines */}
        {COURT_LINES.map(([a, b], i) => {
          const [x1, y1] = px(a[0], a[1]);
          const [x2, y2] = px(b[0], b[1]);
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#4a5568" strokeWidth={1.5} />;
        })}

        {/* Net label */}
        {(() => { const [nx, ny] = px(0, 39); return <text x={nx} y={ny - 6} textAnchor="middle" fill="#4a5568" fontSize={9}>NET</text>; })()}

        {/* Bounce dots */}
        {dots.map(({ s, x, y, r, fill }) => (
          <circle
            key={s.shot_id}
            cx={x} cy={y} r={r}
            fill={fill + (s.shot_id === activeShot ? "ff" : "bb")}
            stroke={s.shot_id === activeShot ? "#fff" : fill}
            strokeWidth={s.shot_id === activeShot ? 2 : 1}
            style={{ cursor: "pointer" }}
            onMouseEnter={() => setHovered(s.shot_id)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => onSelectShot?.(s)}
          />
        ))}
      </svg>

      {/* Hover tooltip */}
      {hoveredShot && (
        <div style={{ fontSize: 11, color: "var(--muted)", textAlign: "center", marginTop: 6 }}>
          #{hoveredShot.shot_number} · {hoveredShot.shot_type} · {hoveredShot.spin_type}
          {hoveredShot.speed_mph ? ` · ${hoveredShot.speed_mph.toFixed(0)} mph` : ""}
          {hoveredShot.quality_score != null ? ` · Q:${hoveredShot.quality_score.toFixed(0)}` : ""}
        </div>
      )}

      {/* Legend */}
      <div className="flex-gap" style={{ justifyContent: "center", marginTop: 10, gap: 16 }}>
        {[["#4ade80", "In"], ["#f87171", "Out"], ["#f59e0b", "Close"]].map(([c, l]) => (
          <div key={l} className="flex-gap" style={{ gap: 5, fontSize: 11, color: "var(--muted)" }}>
            <svg width={10} height={10}><circle cx={5} cy={5} r={4} fill={c} /></svg>
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}
