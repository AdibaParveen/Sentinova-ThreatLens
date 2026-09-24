"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { IndicatorDrawer } from "@/components/IndicatorDrawer";
import { Kpi, PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, SeverityBadge, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Alert, Paged, SocCounters } from "@/lib/types";

export default function SocPage() {
  const [open, setOpen] = useState<string | null>(null);
  const counters = useQuery({ queryKey: ["soc-c"], queryFn: () => api<SocCounters>("/api/v1/soc/counters"), refetchInterval: 15000 });
  const mine = useQuery({ queryKey: ["soc-mine"], queryFn: () => api<Paged<Alert>>("/api/v1/alerts?mine=true&page_size=15"), refetchInterval: 15000 });
  const stream = useQuery({ queryKey: ["soc-new"], queryFn: () => api<Paged<Alert>>("/api/v1/alerts?status=new&page_size=15"), refetchInterval: 15000 });
  const c = counters.data;

  return (
    <div>
      <PageHeader title="SOC analyst workspace" subtitle="Live queue, unassigned work, and high-severity stream." />
      {counters.isLoading ? (
        <Skeleton />
      ) : counters.error ? (
        <ErrorState message="Unable to load SOC counters." onRetry={() => counters.refetch()} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Kpi label="New alerts" value={c?.new_alerts ?? 0} />
          <Kpi label="Unassigned" value={c?.unassigned ?? 0} />
          <Kpi label="My queue" value={c?.my_queue ?? 0} />
          <Kpi label="Critical open" value={c?.critical_alerts ?? 0} />
          <Kpi label="Active incidents" value={c?.active_incidents ?? 0} />
        </div>
      )}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <Queue title="My queue" items={mine.data?.items || []} loading={mine.isLoading} onOpen={setOpen} empty="Nothing assigned to you." />
        <Queue title="Incoming stream" items={stream.data?.items || []} loading={stream.isLoading} onOpen={setOpen} empty="No new alerts." />
      </div>
      {open && <IndicatorDrawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function Queue({
  title,
  items,
  loading,
  onOpen,
  empty,
}: {
  title: string;
  items: Alert[];
  loading: boolean;
  onOpen: (id: string) => void;
  empty: string;
}) {
  return (
    <div className="panel p-4">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {loading && <Skeleton className="h-40" />}
      {!loading && items.length === 0 && <Empty title={empty} />}
      <div className="space-y-2">
        {items.map((a) => (
          <div key={a.id} className="rounded border border-white/10 p-3">
            <div className="flex items-start justify-between gap-2">
              <Link href="/alerts" className="font-medium hover:underline">
                {a.title}
              </Link>
              <SeverityBadge value={a.severity} />
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {a.source} · {fmt(a.created_at)} · {a.status.replaceAll("_", " ")}
            </p>
            {a.indicator && (
              <button className="mt-2 font-mono text-xs text-accent" onClick={() => onOpen(a.indicator!.id)}>
                {a.indicator.value}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
