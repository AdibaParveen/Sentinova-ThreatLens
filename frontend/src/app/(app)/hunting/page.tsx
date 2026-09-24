"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { IndicatorDrawer } from "@/components/IndicatorDrawer";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, SeverityBadge, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import type { Hunt, Indicator, Paged } from "@/lib/types";
import { IOC_TYPES, SEVERITIES } from "@/lib/ui";

export default function HuntingPage() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [severity, setSeverity] = useState("");
  const [name, setName] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [ran, setRan] = useState(false);

  const hunts = useQuery({ queryKey: ["hunts"], queryFn: () => api<Paged<Hunt>>(" /api/v1/hunts".trim()) });
  const results = useQuery({
    queryKey: ["hunt-run", q, type, severity, ran],
    enabled: ran,
    queryFn: async () => {
      const p = new URLSearchParams({ page_size: "50" });
      if (q) p.set("q", q);
      if (type) p.set("type", type);
      if (severity) p.set("severity", severity);
      return api<Paged<Indicator>>(`/api/v1/indicators?${p}`);
    },
  });

  const save = async () => {
    if (!name.trim()) return toast("Name the hunt first", "err");
    try {
      await api("/api/v1/hunts", { method: "POST", body: JSON.stringify({ name, description: "", query: { q, type, severity }, tags: [] }) });
      toast("Hunt saved");
      hunts.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Save failed", "err");
    }
  };

  return (
    <div>
      <PageHeader title="Threat hunting" subtitle="Build queries, save hunts, and pivot into indicators." />
      <div className="panel mb-4 grid gap-2 p-4 md:grid-cols-4">
        <input className="input md:col-span-2" placeholder="Query (value, category, host…)" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">Any type</option>
          {IOC_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">Any severity</option>
          {SEVERITIES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <input className="input" placeholder="Save as…" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="btn-primary" onClick={() => setRan(true)}>
          Run hunt
        </button>
        <button className="btn-ghost" onClick={save}>
          Save hunt
        </button>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="panel p-4">
          <h2 className="text-sm font-semibold">Saved hunts</h2>
          {hunts.isLoading && <Skeleton className="mt-3 h-24" />}
          {hunts.error && <ErrorState message="Cannot load hunts." onRetry={() => hunts.refetch()} />}
          {(hunts.data?.items || []).map((h) => (
            <div key={h.id} className="mt-3 rounded bg-white/5 p-2 text-sm">
              <div className="flex justify-between gap-2">
                <button
                  className="text-left font-medium"
                  onClick={() => {
                    setQ(h.query?.q || "");
                    setType(h.query?.type || "");
                    setSeverity(h.query?.severity || "");
                    setRan(true);
                  }}
                >
                  {h.name}
                </button>
                <button
                  className="text-xs text-critical"
                  onClick={async () => {
                    await api(`/api/v1/hunts/${h.id}`, { method: "DELETE" });
                    hunts.refetch();
                  }}
                >
                  Delete
                </button>
              </div>
              <p className="text-xs text-slate-400">{h.description || JSON.stringify(h.query)}</p>
            </div>
          ))}
          {hunts.data && hunts.data.items.length === 0 && <Empty title="No saved hunts." />}
        </section>
        <section className="panel p-4 lg:col-span-2">
          <h2 className="text-sm font-semibold">Results</h2>
          {results.isFetching && <Skeleton className="mt-3 h-32" />}
          {results.data && results.data.items.length === 0 && <Empty title="No matches." />}
          <div className="mt-2 space-y-2">
            {results.data?.items.map((i) => (
              <button key={i.id} className="flex w-full items-center justify-between rounded bg-white/5 px-3 py-2 text-left text-sm" onClick={() => setOpen(i.id)}>
                <span className="font-mono text-xs">{i.value}</span>
                <span className="flex items-center gap-2">
                  <span className="uppercase text-slate-400">{i.type}</span>
                  <SeverityBadge value={i.severity} />
                </span>
              </button>
            ))}
          </div>
        </section>
      </div>
      {open && <IndicatorDrawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
