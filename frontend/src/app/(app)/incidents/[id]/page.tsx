"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { IndicatorDrawer } from "@/components/IndicatorDrawer";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, SeverityBadge, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { DirectoryUser, Incident } from "@/lib/types";
import { INCIDENT_STATUSES } from "@/lib/ui";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const [note, setNote] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["inc", id], queryFn: () => api<Incident>(`/api/v1/incidents/${id}`) });
  const dir = useQuery({ queryKey: ["dir"], queryFn: () => api<{ items: DirectoryUser[] }>("/api/v1/directory") });

  const patch = async (body: Record<string, unknown>, label: string) => {
    try {
      await api(`/api/v1/incidents/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      toast(label);
      q.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Update failed", "err");
    }
  };

  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error || !q.data) return <ErrorState message="Incident not found." onRetry={() => q.refetch()} />;
  const inc = q.data;

  return (
    <div>
      <PageHeader
        title={inc.title}
        subtitle={`Opened ${fmt(inc.created_at)}`}
        actions={
          <Link className="btn-ghost" href="/incidents">
            All incidents
          </Link>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SeverityBadge value={inc.severity} />
        <select className="input w-auto" value={inc.status} onChange={(e) => patch({ status: e.target.value }, "Status updated")}>
          {INCIDENT_STATUSES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          className="input w-auto"
          value=""
          onChange={(e) => patch({ assignee_id: e.target.value }, "Reassigned")}
        >
          <option value="">{inc.assignee || "Assign owner"}</option>
          {(dir.data?.items || []).map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="panel p-4 lg:col-span-2">
          <h2 className="text-sm font-semibold">Timeline</h2>
          <ol className="mt-3 space-y-3">
            {(inc.timeline || []).map((t) => (
              <li key={t.id} className="border-l border-accent/40 pl-3 text-sm">
                <p className="text-[11px] uppercase text-slate-500">
                  {t.type.replaceAll("_", " ")} · {fmt(t.created_at)}
                </p>
                <p>{t.message}</p>
              </li>
            ))}
          </ol>
          <div className="mt-4 flex gap-2">
            <input className="input" placeholder="Analyst note" value={note} onChange={(e) => setNote(e.target.value)} />
            <button
              className="btn-primary"
              onClick={async () => {
                if (!note.trim()) return;
                try {
                  await api(`/api/v1/incidents/${id}/timeline`, { method: "POST", body: JSON.stringify({ message: note }) });
                  setNote("");
                  toast("Note added");
                  q.refetch();
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Failed", "err");
                }
              }}
            >
              Add
            </button>
          </div>
        </section>
        <section className="panel p-4">
          <h2 className="text-sm font-semibold">Containment checklist</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {(inc.checklist || []).map((c) => (
              <li key={c.id} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={c.done}
                  onChange={async (e) => {
                    await api(`/api/v1/incidents/${id}/checklist/${c.id}`, { method: "PATCH", body: JSON.stringify({ done: e.target.checked }) });
                    q.refetch();
                  }}
                />
                <span className={c.done ? "text-slate-500 line-through" : ""}>{c.label}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <h2 className="text-sm font-semibold">Linked indicators</h2>
          {(inc.indicators || []).map((i) => (
            <button key={i.id} className="mt-2 block font-mono text-xs text-accent" onClick={() => setOpen(i.id)}>
              {i.value} · {i.severity}
            </button>
          ))}
          {!inc.indicators?.length && <p className="mt-2 text-xs text-slate-500">No linked indicators.</p>}
        </section>
        <section className="panel p-4">
          <h2 className="text-sm font-semibold">Internal events</h2>
          {(inc.events || []).map((e) => (
            <p key={e.id} className="mt-2 text-xs text-slate-300">
              {fmt(e.occurred_at)} · {e.type} · {e.source_host} · {e.value}
            </p>
          ))}
          {!inc.events?.length && <p className="mt-2 text-xs text-slate-500">No correlated internal events.</p>}
        </section>
      </div>
      {open && <IndicatorDrawer id={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
