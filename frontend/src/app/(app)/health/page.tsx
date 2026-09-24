"use client";

import { useQuery } from "@tanstack/react-query";
import { Kpi, PageHeader } from "@/components/PageHeader";
import { ErrorState, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";

type Health = {
  api: string;
  database: string;
  redis: string;
  search: string;
  websocket: string;
  worker?: string;
  scheduler?: string;
  version?: string;
  environment?: string;
  time?: string;
  feeds?: { name: string; status: string; last_poll_at: string | null }[];
};

export default function HealthPage() {
  const q = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/api/v1/health/detailed"),
    refetchInterval: 20000,
  });
  const about = useQuery({ queryKey: ["about"], queryFn: () => api<{ product: string; version: string; security: string[] }>("/api/v1/about") });

  if (q.isLoading) return <Skeleton className="h-64" />;
  if (q.error || !q.data) return <ErrorState message="Unable to load system health." onRetry={() => q.refetch()} />;
  const d = q.data;

  return (
    <div>
      <PageHeader title="System health" subtitle={`${d.version || ""} · ${d.environment || ""} · ${fmt(d.time)}`} />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {(["api", "database", "redis", "search", "websocket", "worker", "scheduler"] as const).map((k) => (
          <Kpi key={k} label={k} value={(d[k] as string) || "n/a"} />
        ))}
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Feed collectors</h2>
          <ul className="space-y-2 text-sm">
            {(d.feeds || []).map((f) => (
              <li key={f.name} className="flex justify-between gap-2">
                <span>{f.name}</span>
                <span className="text-slate-400">
                  {f.status} · {fmt(f.last_poll_at)}
                </span>
              </li>
            ))}
            {!(d.feeds || []).length && <p className="text-slate-500">No feed status.</p>}
          </ul>
        </section>
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Platform controls</h2>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
            {(about.data?.security || []).map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
