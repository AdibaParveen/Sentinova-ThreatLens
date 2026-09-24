"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Kpi, PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { ThreatMap } from "@/components/ThreatMap";
import { api } from "@/lib/api";
import type { ExecDash } from "@/lib/types";

const COLORS = ["#e5484d", "#f76808", "#f5d90a", "#30a46c", "#2f6fed", "#94a3b8"];

export default function OverviewPage() {
  const q = useQuery({ queryKey: ["exec"], queryFn: () => api<ExecDash>("/api/v1/dashboards/executive"), refetchInterval: 30000 });
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error || !q.data) return <ErrorState message="Unable to load the executive dashboard." onRetry={() => q.refetch()} />;
  const d = q.data;
  const sev = Object.entries(d.severity_distribution || {}).map(([name, value]) => ({ name, value }));
  const cats = Object.entries(d.categories || {}).map(([name, value]) => ({ name, value }));
  const src = Object.entries(d.sources || {}).map(([name, value]) => ({ name, value }));

  return (
    <div>
      <PageHeader
        title="Executive overview"
        subtitle="Risk is computed from live indicator scores, not static placeholders."
        actions={
          <Link className="btn-ghost" href="/reports">
            Generate report
          </Link>
        }
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi label="Organizational risk" value={`${d.risk_score}/100`} />
        <Kpi label="Critical indicators" value={d.critical_indicators} />
        <Kpi label="High indicators" value={d.high_indicators} />
        <Kpi label="Active incidents" value={d.active_incidents} />
        <Kpi label="Open alerts" value={d.open_alerts} hint={`${d.alerts_resolved} resolved of ${d.alerts_received}`} />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Severity distribution</h2>
          {sev.length === 0 ? (
            <Empty title="No scored indicators" />
          ) : (
            <div className="h-64">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={sev} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={3}>
                    {sev.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#111a2e", border: "1px solid #243354" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Threat categories</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={cats}>
                <CartesianGrid stroke="#243354" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111a2e", border: "1px solid #243354" }} />
                <Bar dataKey="value" fill="#2f6fed" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Intelligence sources</h2>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={src} layout="vertical">
                <CartesianGrid stroke="#243354" horizontal={false} />
                <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <YAxis type="category" dataKey="name" width={110} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111a2e", border: "1px solid #243354" }} />
                <Bar dataKey="value" fill="#4c84f0" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Geographic concentration</h2>
          <ul className="space-y-2 text-sm">
            {Object.entries(d.geographies || {})
              .sort((a, b) => b[1] - a[1])
              .slice(0, 8)
              .map(([k, v]) => (
                <li key={k} className="flex justify-between">
                  <span>{k}</span>
                  <span className="text-slate-400">{v}</span>
                </li>
              ))}
            {!Object.keys(d.geographies || {}).length && <p className="text-slate-500">No geo data yet.</p>}
          </ul>
        </div>
      </div>
      <div className="panel mt-5 p-4">
        <h2 className="mb-3 text-sm font-semibold">Global threat map</h2>
        <ThreatMap points={d.map_points || []} />
      </div>
    </div>
  );
}
