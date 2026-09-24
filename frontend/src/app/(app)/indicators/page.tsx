"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { IndicatorDrawer } from "@/components/IndicatorDrawer";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, SeverityBadge, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Indicator, Paged } from "@/lib/types";
import { IOC_STATUSES, IOC_TYPES, SEVERITIES, TLP } from "@/lib/ui";

export default function IndicatorsPage() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [tlp, setTlp] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<string | null>(null);
  const [create, setCreate] = useState(false);
  const [form, setForm] = useState({ value: "", type: "", tlp: "amber", tags: "", notes: "", attack: "" });

  const params = useMemo(() => {
    const p = new URLSearchParams({ page: String(page), page_size: "25" });
    if (q) p.set("q", q);
    if (type) p.set("type", type);
    if (status) p.set("status", status);
    if (severity) p.set("severity", severity);
    if (tlp) p.set("tlp", tlp);
    return p.toString();
  }, [q, type, status, severity, tlp, page]);

  const list = useQuery({
    queryKey: ["inds", params],
    queryFn: () => api<Paged<Indicator>>(`/api/v1/indicators?${params}`),
  });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api<Indicator>("/api/v1/indicators", {
        method: "POST",
        body: JSON.stringify({
          value: form.value,
          type: form.type || null,
          tlp: form.tlp,
          notes: form.notes || null,
          tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
          attack: form.attack.split(",").map((t) => t.trim()).filter(Boolean),
        }),
      });
      toast("Indicator saved");
      setCreate(false);
      setOpen(created.id);
      list.refetch();
    } catch (ex) {
      toast(ex instanceof Error ? ex.message : "Create failed", "err");
    }
  };

  return (
    <div>
      <PageHeader
        title="Indicators of compromise"
        subtitle="Search, enrich, score, and triage IOCs."
        actions={
          <button className="btn-primary" onClick={() => setCreate((v) => !v)}>
            {create ? "Close form" : "Add indicator"}
          </button>
        }
      />
      {create && (
        <form onSubmit={submit} className="panel mb-4 grid gap-3 p-4 md:grid-cols-2">
          <input className="input md:col-span-2" required placeholder="Value (IP, domain, URL, hash, CVE…)" value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} />
          <select className="input" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option value="">Auto-detect type</option>
            {IOC_TYPES.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <select className="input" value={form.tlp} onChange={(e) => setForm({ ...form, tlp: e.target.value })}>
            {TLP.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <input className="input" placeholder="Tags (comma separated)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
          <input className="input" placeholder="ATT&CK IDs (e.g. T1059.001)" value={form.attack} onChange={(e) => setForm({ ...form, attack: e.target.value })} />
          <textarea className="input md:col-span-2" placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          <button className="btn-primary md:col-span-2">Save indicator</button>
        </form>
      )}
      <div className="mb-4 grid gap-2 md:grid-cols-5">
        <input className="input" placeholder="Search value or category" value={q} onChange={(e) => { setPage(1); setQ(e.target.value); }} />
        <select className="input" value={type} onChange={(e) => { setPage(1); setType(e.target.value); }}>
          <option value="">All types</option>
          {IOC_TYPES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="input" value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          <option value="">All statuses</option>
          {IOC_STATUSES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="input" value={severity} onChange={(e) => { setPage(1); setSeverity(e.target.value); }}>
          <option value="">All severities</option>
          {SEVERITIES.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="input" value={tlp} onChange={(e) => { setPage(1); setTlp(e.target.value); }}>
          <option value="">All TLP</option>
          {TLP.map((t) => <option key={t}>{t}</option>)}
        </select>
      </div>
      {list.isLoading && <Skeleton className="h-64" />}
      {list.error && <ErrorState message="Unable to load indicators." onRetry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && <Empty title="No indicators match these filters." />}
      {list.data && list.data.items.length > 0 && (
        <div className="table-wrap panel">
          <table className="data">
            <thead>
              <tr>
                <th>Value</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Score</th>
                <th>Status</th>
                <th>TLP</th>
                <th>Last seen</th>
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((i) => (
                <tr key={i.id} className="cursor-pointer hover:bg-white/5" onClick={() => setOpen(i.id)}>
                  <td className="font-mono text-xs">{i.value}</td>
                  <td className="uppercase">{i.type}</td>
                  <td><SeverityBadge value={i.severity} /></td>
                  <td>{i.severity_score}</td>
                  <td>{i.status}</td>
                  <td className="uppercase">{i.tlp}</td>
                  <td className="text-xs text-slate-400">{fmt(i.last_seen)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="text-slate-400">{list.data?.total ?? 0} total</span>
        <div className="flex gap-2">
          <button className="btn-ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
          <button className="btn-ghost" disabled={(list.data?.items.length || 0) < 25} onClick={() => setPage((p) => p + 1)}>Next</button>
        </div>
      </div>
      {open && <IndicatorDrawer id={open} onClose={() => setOpen(null)} onChanged={() => list.refetch()} />}
    </div>
  );
}
