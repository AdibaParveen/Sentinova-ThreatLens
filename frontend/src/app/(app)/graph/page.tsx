"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { RelationGraph } from "@/components/RelationGraph";
import { ErrorState, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import type { GraphData } from "@/lib/types";

export default function GraphPage() {
  const q = useQuery({ queryKey: ["graph"], queryFn: () => api<GraphData>("/api/v1/graph") });
  return (
    <div>
      <PageHeader title="Relationship graph" subtitle="Infrastructure, malware, and campaign links between indicators." />
      {q.isLoading && <Skeleton className="h-96" />}
      {q.error && <ErrorState message="Unable to load the graph." onRetry={() => q.refetch()} />}
      {q.data && (
        <div className="panel p-2">
          <RelationGraph data={q.data} height={640} />
        </div>
      )}
    </div>
  );
}
