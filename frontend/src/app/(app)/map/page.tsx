"use client";

import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { ThreatMap } from "@/components/ThreatMap";
import { ErrorState, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import type { ExecDash } from "@/lib/types";

export default function MapPage() {
  const q = useQuery({ queryKey: ["exec-map"], queryFn: () => api<ExecDash>("/api/v1/dashboards/executive") });
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error || !q.data) return <ErrorState message="Unable to load the threat map." onRetry={() => q.refetch()} />;
  return (
    <div>
      <PageHeader title="Global threat map" subtitle="Geolocated indicators from live scoring, not static demo pins." />
      <div className="panel p-4">
        <ThreatMap points={q.data.map_points || []} />
      </div>
    </div>
  );
}
