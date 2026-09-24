"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Kpi, PageHeader } from "@/components/PageHeader";
import { ErrorState, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import type { ExecDash, Paged, Feed } from "@/lib/types";

export default function IntelPage() {
  const dash = useQuery({ queryKey: ["exec"], queryFn: () => api<ExecDash>("/api/v1/dashboards/executive") });
  const feeds = useQuery({
    queryKey: ["feeds-intel"],
    queryFn: () => api<Paged<Feed>>("/api/v1/feeds"),
    retry: false,
  });

  if (dash.isLoading) return <Skeleton className="h-64" />;
  if (dash.error || !dash.data) return <ErrorState message="Unable to load intelligence summary." onRetry={() => dash.refetch()} />;
  const d = dash.data;

  return (
    <div>
      <PageHeader
        title="Threat intelligence"
        subtitle="Pivot from scored indicators into feeds, ATT&CK coverage, and exports."
        actions={
          <>
            <Link className="btn-ghost" href="/indicators">
              Indicators
            </Link>
            <Link className="btn-ghost" href="/reports">
              Exports
            </Link>
          </>
        }
      />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Critical IOCs" value={d.critical_indicators} />
        <Kpi label="High IOCs" value={d.high_indicators} />
        <Kpi label="Open alerts" value={d.open_alerts} />
        <Kpi label="Active incidents" value={d.active_incidents} />
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Sources</h2>
          <ul className="space-y-2 text-sm">
            {Object.entries(d.sources || {}).map(([k, v]) => (
              <li key={k} className="flex justify-between">
                <span>{k}</span>
                <span className="text-slate-400">{v}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Feed health</h2>
          {feeds.error && <p className="text-sm text-slate-400">Feed management is limited to privileged roles.</p>}
          {(feeds.data?.items || []).map((f) => (
            <p key={f.id} className="mb-1 flex justify-between text-sm">
              <span>{f.name}</span>
              <span className="text-slate-400">{f.status}</span>
            </p>
          ))}
          <Link className="mt-3 inline-block text-sm text-accent" href="/feeds">
            Manage feeds
          </Link>
        </section>
      </div>
    </div>
  );
}
