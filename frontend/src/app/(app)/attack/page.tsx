"use client";

import { useQuery } from "@tanstack/react-query";
import { AttackMatrix } from "@/components/AttackMatrix";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState, Skeleton } from "@/components/States";
import { api } from "@/lib/api";
import type { AttackTech } from "@/lib/types";

export default function AttackPage() {
  const q = useQuery({ queryKey: ["attack"], queryFn: () => api<{ techniques: AttackTech[] }>("/api/v1/attack") });
  const techs = q.data?.techniques || [];
  const covered = techs.filter((t) => t.covered).length;
  return (
    <div>
      <PageHeader
        title="MITRE ATT&CK coverage"
        subtitle="Highlighted techniques are mapped from live indicators. Unmapped cells are not invented."
      />
      {q.isLoading && <Skeleton className="h-96" />}
      {q.error && <ErrorState message="Unable to load ATT&CK coverage." onRetry={() => q.refetch()} />}
      {q.data && (
        <>
          <p className="mb-4 text-sm text-slate-400">
            {covered} of {techs.length} catalogued techniques have indicator mappings.
          </p>
          <div className="panel p-4">
            <AttackMatrix techniques={techs} />
          </div>
        </>
      )}
    </div>
  );
}
