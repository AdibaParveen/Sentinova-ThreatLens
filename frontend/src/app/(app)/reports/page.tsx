"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api, downloadAuthenticated } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Paged, ReportRow } from "@/lib/types";
import { TLP } from "@/lib/ui";

const TYPES = ["executive", "soc", "incident", "hunting", "indicator"];
const FORMATS = ["pdf", "json"];

export default function ReportsPage() {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [type, setType] = useState("executive");
  const [format, setFormat] = useState("pdf");
  const [tlp, setTlp] = useState("red");

  const list = useQuery({
    queryKey: ["reports"],
    queryFn: () => api<Paged<ReportRow>>("/api/v1/reports"),
  });

  const generate = async () => {
    try {
      await api("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({ report_type: type, format, title: title || undefined, tlp_max: tlp }),
      });
      toast("Report generated");
      setTitle("");
      list.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Generate failed", "err");
    }
  };

  const pull = async (path: string, filename: string) => {
    try {
      await downloadAuthenticated(path, filename);
      toast("Download started");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Download failed", "err");
    }
  };

  return (
    <div>
      <PageHeader title="Reports & exports" subtitle="Generate snapshots and download CSV, STIX, or PDF packages." />
      <div className="panel mb-4 grid gap-2 p-4 md:grid-cols-5">
        <input className="input" placeholder="Title (optional)" value={title} onChange={(e) => setTitle(e.target.value)} />
        <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
          {TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select className="input" value={format} onChange={(e) => setFormat(e.target.value)}>
          {FORMATS.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select className="input" value={tlp} onChange={(e) => setTlp(e.target.value)}>
          {TLP.map((t) => (
            <option key={t} value={t}>
              TLP max {t}
            </option>
          ))}
        </select>
        <button className="btn-primary" onClick={generate}>
          Generate
        </button>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <button className="btn-ghost" onClick={() => pull(`/api/v1/export/csv?tlp_max=${tlp}`, "indicators.csv")}>
          Export CSV
        </button>
        <button className="btn-ghost" onClick={() => pull(`/api/v1/export/stix?tlp_max=${tlp}`, "indicators.stix.json")}>
          Export STIX
        </button>
      </div>
      {list.isLoading && <Skeleton className="h-48" />}
      {list.error && <ErrorState message="Unable to load reports." onRetry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && <Empty title="No reports generated yet." />}
      <div className="table-wrap panel">
        <table className="data">
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Format</th>
              <th>Status</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(list.data?.items || []).map((r) => (
              <tr key={r.id}>
                <td>{r.title}</td>
                <td className="capitalize">{r.type}</td>
                <td>{r.format}</td>
                <td>{r.status}</td>
                <td className="text-xs">{fmt(r.created_at)}</td>
                <td>
                  <button className="btn-primary" onClick={() => pull(`/api/v1/reports/${r.id}/pdf`, `${r.title.replaceAll(" ", "-")}.pdf`)}>
                    PDF
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
