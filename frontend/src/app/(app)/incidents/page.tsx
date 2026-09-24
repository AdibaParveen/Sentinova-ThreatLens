"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, SeverityBadge, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Incident, Paged } from "@/lib/types";

export default function IncidentsPage() {
  const q = useQuery({ queryKey: ["incidents"], queryFn: () => api<Paged<Incident>>("/api/v1/incidents") });
  return (
    <div>
      <PageHeader title="Incident response" subtitle="Cases, timelines, and containment checklists." />
      {q.isLoading && <Skeleton className="h-64" />}
      {q.error && <ErrorState message="Unable to load incidents." onRetry={() => q.refetch()} />}
      {q.data && q.data.items.length === 0 && <Empty title="No incidents yet." hint="Escalate an alert to open a case." />}
      <div className="table-wrap panel">
        {q.data && q.data.items.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>Title</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Assignee</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {q.data.items.map((i) => (
                <tr key={i.id} className="hover:bg-white/5">
                  <td>
                    <Link className="hover:underline" href={`/incidents/${i.id}`}>
                      {i.title}
                    </Link>
                  </td>
                  <td><SeverityBadge value={i.severity} /></td>
                  <td className="capitalize">{i.status}</td>
                  <td>{i.assignee || "—"}</td>
                  <td className="text-xs text-slate-400">{fmt(i.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
