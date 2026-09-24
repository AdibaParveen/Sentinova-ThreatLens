"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, Skeleton } from "@/components/States";
import { api } from "@/lib/api";

type Heat = Record<string, Record<string, number>>;

const SEV = ["critical", "high", "medium", "low"];
const TINT: Record<string, string> = {
  critical: "bg-critical/40",
  high: "bg-high/40",
  medium: "bg-yellow-500/30",
  low: "bg-low/30",
};

function Grid({ title, data }: { title: string; data: Heat }) {
  const rows = Object.keys(data).sort();
  return (
    <section className="panel p-4">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Bucket</th>
              {SEV.map((s) => (
                <th key={s}>{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row}>
                <td>{row}</td>
                {SEV.map((s) => {
                  const n = data[row]?.[s] || 0;
                  return (
                    <td key={s}>
                      <span className={`inline-block min-w-[2rem] rounded px-2 py-0.5 text-center ${n ? TINT[s] : "bg-white/5"}`}>{n}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function HeatmapPage() {
  const q = useQuery({
    queryKey: ["heatmap"],
    queryFn: () => api<{ categories: Heat; geographies: Heat; types: Heat }>("/api/v1/dashboards/heatmap"),
  });
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error || !q.data) return <ErrorState message="Unable to load heatmap." onRetry={() => q.refetch()} />;
  return (
    <div>
      <PageHeader title="Threat heatmap" subtitle="Counts by category, geography, and indicator type." />
      <div className="space-y-4">
        <Grid title="Categories" data={q.data.categories} />
        <Grid title="Geographies" data={q.data.geographies} />
        <Grid title="Types" data={q.data.types} />
      </div>
    </div>
  );
}
