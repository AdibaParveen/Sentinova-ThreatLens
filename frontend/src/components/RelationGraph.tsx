"use client";

import { useEffect, useRef } from "react";
import type { GraphData } from "@/lib/types";

export function RelationGraph({ data, height = 520 }: { data: GraphData; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let network: { destroy: () => void } | null = null;
    (async () => {
      if (!ref.current) return;
      const [{ Network }, { DataSet }] = await Promise.all([import("vis-network/standalone"), import("vis-data")]);
      const nodes = new DataSet(
        data.nodes.map((n) => ({
          id: n.id,
          label: n.label.length > 28 ? n.label.slice(0, 26) + "…" : n.label,
          title: `${n.label} (${n.type})`,
          color: n.severity >= 75 ? "#e5484d" : n.severity >= 50 ? "#f76808" : "#2f6fed",
          font: { color: "#e2e8f0", size: 12 },
        }))
      );
      const edges = new DataSet(
        data.edges.map((e, i) => ({
          id: i,
          from: e.source,
          to: e.target,
          label: e.type,
          font: { color: "#94a3b8", size: 10 },
          color: { color: "#475569" },
          arrows: "to",
        }))
      );
      network = new Network(ref.current, { nodes, edges }, {
        physics: { stabilization: true, barnesHut: { gravitationalConstant: -2800 } },
        interaction: { hover: true, tooltipDelay: 80 },
        edges: {
  smooth: {
    enabled: true,
    type: "dynamic",
    roundness: 0.5,
  },
},
      });
    })();
    return () => network?.destroy();
  }, [data]);

  if (!data.nodes.length) {
    return <p className="p-6 text-sm text-slate-400">No relationship edges have been recorded yet.</p>;
  }

  return <div ref={ref} style={{ height }} className="w-full rounded-lg border border-white/10 bg-navy-950" />;
}
