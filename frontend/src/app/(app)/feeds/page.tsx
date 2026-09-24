"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Feed, Paged } from "@/lib/types";

const FEED_TYPES = ["otx", "abuseipdb", "urlhaus", "malwarebazaar", "threatfox", "feodo", "attack", "cisa_kev", "custom"];

export default function FeedsPage() {
  const toast = useToast();
  const [name, setName] = useState("");
  const [provider, setProvider] = useState("");
  const [feedType, setFeedType] = useState("custom");
  const [interval, setInterval] = useState(60);

  const list = useQuery({
    queryKey: ["feeds"],
    queryFn: () => api<Paged<Feed>>("/api/v1/feeds"),
    refetchInterval: 30000,
  });

  const add = async () => {
    if (!name.trim() || !provider.trim()) return toast("Name and provider are required", "err");
    try {
      await api("/api/v1/feeds", {
        method: "POST",
        body: JSON.stringify({ name, provider, feed_type: feedType, poll_interval_minutes: interval }),
      });
      toast("Feed added");
      setName("");
      setProvider("");
      list.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Create failed", "err");
    }
  };

  const patch = async (id: string, body: Record<string, unknown>, ok: string) => {
    try {
      await api(`/api/v1/feeds/${id}`, { method: "PATCH", body: JSON.stringify(body) });
      toast(ok);
      list.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Update failed", "err");
    }
  };

  return (
    <div>
      <PageHeader title="Threat intelligence feeds" subtitle="Enable, poll, and monitor inbound sources." />
      <div className="panel mb-4 grid gap-2 p-4 md:grid-cols-5">
        <input className="input" placeholder="Feed name" value={name} onChange={(e) => setName(e.target.value)} />
        <input className="input" placeholder="Provider" value={provider} onChange={(e) => setProvider(e.target.value)} />
        <select className="input" value={feedType} onChange={(e) => setFeedType(e.target.value)}>
          {FEED_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <input className="input" type="number" min={5} value={interval} onChange={(e) => setInterval(Number(e.target.value))} />
        <button className="btn-primary" onClick={add}>
          Add feed
        </button>
      </div>
      {list.isLoading && <Skeleton className="h-64" />}
      {list.error && <ErrorState message="Unable to load feeds." onRetry={() => list.refetch()} />}
      {list.data && list.data.items.length === 0 && <Empty title="No feeds configured." />}
      <div className="table-wrap panel">
        <table className="data">
          <thead>
            <tr>
              <th>Name</th>
              <th>Provider</th>
              <th>Type</th>
              <th>Status</th>
              <th>Last poll</th>
              <th>Next</th>
              <th>Received</th>
              <th>Errors</th>
              <th>Interval</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(list.data?.items || []).map((f) => (
              <tr key={f.id}>
                <td>
                  <p className="font-medium">{f.name}</p>
                  {f.last_error && <p className="text-xs text-critical">{f.last_error}</p>}
                </td>
                <td>{f.provider}</td>
                <td className="font-mono text-xs">{f.type}</td>
                <td>
                  <span className={f.status === "healthy" ? "text-low" : "text-high"}>{f.status}</span>
                  {!f.enabled && <span className="ml-1 text-xs text-slate-500">paused</span>}
                </td>
                <td className="text-xs">{fmt(f.last_poll_at)}</td>
                <td className="text-xs">{fmt(f.next_poll_at)}</td>
                <td>{f.indicators_received}</td>
                <td>{f.error_count}</td>
                <td>
                  <input
                    className="input w-20"
                    type="number"
                    defaultValue={f.poll_interval_minutes}
                    onBlur={(e) => {
                      const v = Number(e.target.value);
                      if (v && v !== f.poll_interval_minutes) patch(f.id, { poll_interval_minutes: v }, "Interval updated");
                    }}
                  />
                </td>
                <td>
                  <div className="flex flex-wrap gap-2">
                    <button className="btn-ghost" onClick={() => patch(f.id, { enabled: !f.enabled }, f.enabled ? "Paused" : "Enabled")}>
                      {f.enabled ? "Pause" : "Enable"}
                    </button>
                    <button
                      className="btn-primary"
                      onClick={async () => {
                        try {
                          const r = await api<{ ingested: number }>(`/api/v1/feeds/${f.id}/poll`, { method: "POST" });
                          toast(`Polled · ${r.ingested} ingested`);
                          list.refetch();
                        } catch (e) {
                          toast(e instanceof Error ? e.message : "Poll failed", "err");
                        }
                      }}
                    >
                      Poll now
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
