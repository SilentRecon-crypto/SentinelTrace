import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import type { RiskTrendPoint } from "@/types";

const SERIES = [
  { key: "critical", color: "var(--color-critical)", label: "Critical" },
  { key: "high", color: "var(--color-high)", label: "High" },
  { key: "medium", color: "var(--color-medium)", label: "Medium" },
  { key: "low", color: "var(--color-low)", label: "Low" },
] as const;

export function RiskTrendChart({ data, range }: { data: RiskTrendPoint[]; range: string }) {
  const chartData = data.map((d) => ({
    ...d,
    label:
      range === "24H"
        ? new Date(d.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", hour12: false })
        : new Date(d.timestamp).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }),
  }));

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          {SERIES.map((s) => (
            <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="0" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: "var(--color-text-tertiary)", fontSize: 10.5 }} axisLine={{ stroke: "var(--color-border)" }} tickLine={false} interval="preserveStartEnd" />
        <YAxis tick={{ fill: "var(--color-text-tertiary)", fontSize: 10.5 }} axisLine={false} tickLine={false} width={28} />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface-raised)",
            border: "1px solid var(--color-border-strong)",
            borderRadius: 4,
            fontSize: 12,
            padding: "8px 10px",
          }}
          labelStyle={{ color: "var(--color-text-secondary)", marginBottom: 4, fontSize: 11 }}
          itemStyle={{ padding: 0 }}
        />
        {SERIES.map((s) => (
          <Area
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stackId="1"
            stroke={s.color}
            strokeWidth={1.4}
            fill={`url(#grad-${s.key})`}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
