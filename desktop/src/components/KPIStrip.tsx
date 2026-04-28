import { Session, Shot } from "@/types";

interface Props {
  session: Session;
  shots: Shot[];
}

export function KPIStrip({ session, shots }: Props) {
  const inPct = shots.length
    ? Math.round((shots.filter((s) => s.is_in === 1 || s.is_in === true).length / shots.length) * 100)
    : null;
  const netPct = shots.length
    ? Math.round((shots.filter((s) => s.cleared_net === 1 || s.cleared_net === true).length / shots.length) * 100)
    : null;

  return (
    <div className="kpi-row">
      <KPI label="Total Shots" value={session.total_shots || shots.length} className="info" />
      <KPI label="Avg Speed" value={session.avg_speed_mph ? `${session.avg_speed_mph} mph` : "—"} className="info" />
      <KPI label="In-Bounds" value={inPct !== null ? `${inPct}%` : "—"} className="good" />
      <KPI label="Net Clearance" value={netPct !== null ? `${netPct}%` : "—"} className="good" />
    </div>
  );
}

function KPI({ label, value, className }: { label: string; value: string | number; className?: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value ${className ?? ""}`}>{value}</div>
    </div>
  );
}
