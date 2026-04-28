import { useState } from "react";
import { Shot } from "@/types";

type SortKey = keyof Shot;

interface Props {
  shots: Shot[];
  activeShot?: string;
  onSelectShot?: (shot: Shot) => void;
}

export function ShotTable({ shots, activeShot, onSelectShot }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("shot_number");
  const [asc, setAsc] = useState(true);

  function handleSort(key: SortKey) {
    if (sortKey === key) setAsc((a) => !a);
    else { setSortKey(key); setAsc(true); }
  }

  const sorted = [...shots].sort((a, b) => {
    const va = (a[sortKey] as number | string) ?? 0;
    const vb = (b[sortKey] as number | string) ?? 0;
    return asc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });

  function sortIcon(key: SortKey) {
    if (sortKey !== key) return " ↕";
    return asc ? " ↑" : " ↓";
  }

  return (
    <div style={{ overflowX: "auto", maxHeight: 380, overflowY: "auto" }}>
      <table className="shot-table">
        <thead>
          <tr>
            {(
              [
                ["shot_number", "#"],
                ["start_time_sec", "Time"],
                ["shot_type", "Type"],
                ["spin_type", "Spin"],
                ["speed_mph", "Speed"],
                ["rpm_estimate", "RPM"],
                ["net_clearance_inches", "Net (in)"],
                ["is_in", "In/Out"],
                ["quality_score", "Q"],
              ] as [SortKey, string][]
            ).map(([key, label]) => (
              <th key={key} onClick={() => handleSort(key)}>
                {label}{sortIcon(key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => {
            const isClose = s.is_close_call === 1 || s.is_close_call === true;
            const isIn = s.is_in === 1 || s.is_in === true;
            const inClass = isClose ? "in-close" : isIn ? "in-yes" : "in-no";
            const inLabel = isClose ? "Close" : isIn ? "In" : "Out";
            return (
              <tr
                key={s.shot_id}
                className={s.shot_id === activeShot ? "active-shot" : ""}
                onClick={() => onSelectShot?.(s)}
              >
                <td>{s.shot_number}</td>
                <td>{s.start_time_sec != null ? `${s.start_time_sec.toFixed(1)}s` : "—"}</td>
                <td>{s.shot_type}</td>
                <td>{s.spin_type}</td>
                <td>{s.speed_mph != null ? `${s.speed_mph.toFixed(0)} mph` : "—"}</td>
                <td>{s.rpm_estimate != null ? Math.round(s.rpm_estimate) : "—"}</td>
                <td>{s.net_clearance_inches != null ? s.net_clearance_inches.toFixed(1) : "—"}</td>
                <td className={inClass}>{inLabel}</td>
                <td>{s.quality_score != null ? s.quality_score.toFixed(0) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
