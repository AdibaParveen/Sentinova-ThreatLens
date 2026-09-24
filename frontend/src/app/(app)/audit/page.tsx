"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { AuditRow, Paged } from "@/lib/types";

export default function AuditPage() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const list = useQuery({
    queryKey: ["audit", submitted],
    queryFn: () => api<Paged<AuditRow>>(`/api/v1/audit${submitted ? `?q=${encodeURIComponent(submitted)}` : ""}`),
  });

  const selected = useMemo(() => (list.data?.items || []).find((r) => r.id === open), [list.data, open]);

  const exportCsv = () => {
    const rows = list.data?.items || [];
    if (!rows.length) return toast("Nothing to export", "err");
    const header = ["timestamp", "user", "role", "action", "resource", "resource_id", "ip_address", "correlation_id", "result"];
    const body = rows.map((r) => header.map((h) => JSON.stringify((r as Record<string, unknown>)[h] ?? "")).join(","));
    const blob = new Blob([[header.join(","), ...body].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "threatlens-audit.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader
        title="Audit log"
        subtitle="Append-only trail of privileged and operator actions."
        actions={
          <button className="btn-ghost" onClick={exportCsv}>
            Export CSV
          </button>
        }
      />
      <form
        className="mb-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(q);
        }}
      >
        <input className="input" placeholder="Search action, user, or correlation ID" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn-primary" type="submit">
          Search
        </button>
      </form>
      {list.isLoading && <Skeleton className="h-64" />}
      {list.error && <ErrorState message="Unable to load audit logs." onRetry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && <Empty title="No matching audit events." />}
      <div className="table-wrap panel">
        <table className="data">
          <thead>
            <tr>
              <th>Time</th>
              <th>User</th>
              <th>Role</th>
              <th>Action</th>
              <th>Resource</th>
              <th>IP</th>
              <th>Result</th>
              <th>Correlation</th>
            </tr>
          </thead>
          <tbody>
            {(list.data?.items || []).map((r) => (
              <tr key={r.id} className="cursor-pointer hover:bg-white/5" onClick={() => setOpen(r.id)}>
                <td className="whitespace-nowrap text-xs">{fmt(r.timestamp)}</td>
                <td>{r.user}</td>
                <td className="capitalize">{r.role.replaceAll("_", " ")}</td>
                <td className="font-mono text-xs">{r.action}</td>
                <td className="text-xs">
                  {r.resource}
                  {r.resource_id ? ` · ${r.resource_id.slice(0, 8)}` : ""}
                </td>
                <td className="font-mono text-xs">{r.ip_address || "—"}</td>
                <td>{r.result}</td>
                <td className="font-mono text-xs">{r.correlation_id?.slice(0, 8) || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selected && (
        <div className="panel mt-4 p-4">
          <div className="mb-2 flex justify-between">
            <h2 className="text-sm font-semibold">Event detail</h2>
            <button className="btn-ghost" onClick={() => setOpen(null)}>
              Close
            </button>
          </div>
          <pre className="overflow-auto text-xs text-slate-300">{JSON.stringify(selected, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
