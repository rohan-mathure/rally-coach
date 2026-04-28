import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { Shot } from "@/types";

const COLORS: Record<string, string> = {
  forehand: "#60a5fa",
  backhand: "#a78bfa",
  volley:   "#34d399",
  overhead: "#fbbf24",
  unknown:  "#6b7280",
  topspin:  "#4ade80",
  underspin: "#f87171",
  flat:     "#94a3b8",
};

const TOOLTIP_STYLE = {
  backgroundColor: "#1a1d26",
  border: "1px solid #2d3347",
  borderRadius: 8,
  color: "#e2e8f0",
  fontSize: 12,
};

const AXIS_TICK = { fill: "#8892a4", fontSize: 11 };

function countBy<K extends string>(items: Shot[], key: (s: Shot) => K) {
  const counts: Record<string, number> = {};
  items.forEach((s) => {
    const k = key(s) || "unknown";
    counts[k] = (counts[k] || 0) + 1;
  });
  return Object.entries(counts).map(([name, value]) => ({ name, value }));
}

function histogram(values: number[], bins: number) {
  if (!values.length) return [];
  const min = Math.floor(Math.min(...values));
  const max = Math.ceil(Math.max(...values));
  const size = Math.max(1, Math.round((max - min) / bins));
  const buckets: Record<number, number> = {};
  for (let i = min; i <= max; i += size) buckets[i] = 0;
  values.forEach((v) => {
    const b = Math.floor((v - min) / size) * size + min;
    buckets[b] = (buckets[b] ?? 0) + 1;
  });
  return Object.entries(buckets)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([k, v]) => ({ name: `${k}–${Number(k) + size}`, value: v }));
}

export function ShotTypeChart({ shots }: { shots: Shot[] }) {
  const data = countBy(shots, (s) => s.shot_type);
  return (
    <ResponsiveContainer width="100%" height={160}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60} innerRadius={36}>
          {data.map((d) => <Cell key={d.name} fill={COLORS[d.name] ?? "#6b7280"} />)}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend iconSize={8} formatter={(v) => <span style={{ color: "#e2e8f0", fontSize: 11 }}>{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function SpinTypeChart({ shots }: { shots: Shot[] }) {
  const data = countBy(shots, (s) => s.spin_type);
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
        <XAxis dataKey="name" tick={AXIS_TICK} />
        <YAxis tick={AXIS_TICK} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
          {data.map((d) => <Cell key={d.name} fill={COLORS[d.name] ?? "#6b7280"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function SpeedHistogram({ shots }: { shots: Shot[] }) {
  const speeds = shots.map((s) => s.speed_mph).filter((v): v is number => v != null);
  const data = histogram(speeds, 10);
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
        <XAxis dataKey="name" tick={{ ...AXIS_TICK, fontSize: 9 }} />
        <YAxis tick={AXIS_TICK} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="value" fill="#60a5fa" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function QualityHistogram({ shots }: { shots: Shot[] }) {
  const qs = shots.map((s) => s.quality_score).filter((v): v is number => v != null);
  const data = histogram(qs, 10);
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: -20 }}>
        <XAxis dataKey="name" tick={{ ...AXIS_TICK, fontSize: 9 }} />
        <YAxis tick={AXIS_TICK} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="value" fill="#4ade80" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
