"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { IndicatorDrawer } from "@/components/IndicatorDrawer";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, SeverityBadge, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Alert, DirectoryUser, Paged } from "@/lib/types";
import { ALERT_STATUSES, SEVERITIES } from "@/lib/ui";

export default function AlertsPage() {
  const toast = useToast();
  const router = useRouter();
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [mine, setMine] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [note, setNote] = useState<Record<string, string>>({});

  const params = useMemo(() => {
    const p = new URLSearchParams({ page_size: "40" });
    if (severity) p.set("severity", severity);
    if (status) p.set("status", status);
    if (source) p.set("source", source);
    if (mine) p.set("mine", "true");
    return p.toString();
  }, [severity, status, source, mine]);

  const list = useQuery({ queryKey: ["alerts", params], queryFn: () => api<Paged<Alert>>(`/api/v1/alerts?${params}`), refetchInterval: 20000 });
  const dir = useQuery({ queryKey: ["dir"], queryFn: () => api<{ items: DirectoryUser[] }>("/api/v1/directory") });

  const patch = async (id: string, body: Record<string, unknown>, label: string) => {
    try {
      await api(`/api/v1/alerts/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      toast(label);
      list.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Update failed", "err");
    }
  };

  return (
    <div>
      <PageHeader title="Alerts" subtitle="Lifecycle, assignment, and escalation into incidents." />
      <div className="mb-4 grid gap-2 md:grid-cols-4">
        <select className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All severities</option>
          {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {ALERT_STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <input className="input" placeholder="Source contains…" value={source} onChange={(e) => setSource(e.target.value)} />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
          Assigned to me
        </label>
      </div>
      {list.isLoading && <Skeleton className="h-64" />}
      {list.error && <ErrorState message="Unable to load alerts." onRetry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && <Empty title="No alerts match these filters." />}
      <div className="space-y-3">
        {list.data?.items.map((a) => (
          <div key={a.id} className="panel p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-medium">{a.title}</h2>
                  <SeverityBadge value={a.severity} />
                  <span className="text-xs uppercase text-slate-400">{a.status.replaceAll("_", " ")}</span>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {a.source} · {a.category} · {fmt(a.created_at)}
                  {a.assignee ? ` · ${a.assignee.name}` : " · unassigned"}
                </p>
                {a.indicator && (
                  <button className="mt-2 font-mono text-xs text-accent" onClick={() => setOpen(a.indicator!.id)}>
                    {a.indicator.value}
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <select className="input w-auto" value={a.status} onChange={(e) => patch(a.id, { status: e.target.value }, "Status updated")}>
                  {ALERT_STATUSES.map((s) => <option key={s}>{s}</option>)}
                </select>
                <select
                  className="input w-auto"
                  value={a.assignee?.id || ""}
                  onChange={(e) => patch(a.id, { assignee_id: e.target.value }, "Assigned")}
                >
                  <option value="">Assign…</option>
                  {(dir.data?.items || []).map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
                <button
                  className="btn-primary"
                  onClick={async () => {
                    try {
                      const r = await api<{ incident_id: string }>(`/api/v1/alerts/${a.id}/escalate`, { method: "POST" });
                      toast("Escalated to incident");
                      router.push(`/incidents/${r.incident_id}`);
                    } catch (e) {
                      toast(e instanceof Error ? e.message : "Escalate failed", "err");
                    }
                  }}
                >
                  Escalate
                </button>
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <input className="input" placeholder="Add note" value={note[a.id] || ""} onChange={(e) => setNote((s) => ({ ...s, [a.id]: e.target.value }))} />
              <button className="btn-ghost" onClick={() => patch(a.id, { notes: note[a.id] }, "Note saved")}>
                Save note
              </button>
            </div>
            {a.notes && <pre className="mt-2 whitespace-pre-wrap text-xs text-slate-400">{a.notes}</pre>}
          </div>
        ))}
      </div>
      {open && <IndicatorDrawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
