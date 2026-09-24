"use client";

import type { AttackTech } from "@/lib/types";

const ORDER = [
  "Initial Access",
  "Execution",
  "Persistence",
  "Privilege Escalation",
  "Defense Evasion",
  "Credential Access",
  "Discovery",
  "Lateral Movement",
  "Collection",
  "Command and Control",
  "Exfiltration",
  "Impact",
];

export function AttackMatrix({ techniques }: { techniques: AttackTech[] }) {
  const tactics = Array.from(new Set([...ORDER, ...techniques.map((t) => t.tactic)]));
  const byTactic = Object.fromEntries(tactics.map((t) => [t, techniques.filter((x) => x.tactic === t)]));
  const visible = tactics.filter((t) => (byTactic[t] || []).length > 0);

  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-max gap-2">
        {visible.map((tactic) => (
          <div key={tactic} className="w-40 shrink-0">
            <p className="mb-2 h-10 text-xs font-semibold uppercase leading-tight text-slate-400">{tactic}</p>
            <div className="space-y-1">
              {(byTactic[tactic] || []).map((t) => (
                <div
                  key={t.id}
                  title={t.name}
                  className={`rounded px-2 py-2 text-[11px] ${
                    t.covered ? "bg-accent/30 text-white" : "bg-white/5 text-slate-400"
                  }`}
                >
                  <p className="font-mono">{t.id}</p>
                  <p className="truncate">{t.name}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HeatGrid({
  rows,
  cols,
  values,
  rowLabel,
}: {
  rows: string[];
  cols: string[];
  values: Record<string, Record<string, number>>;
  rowLabel?: string;
}) {
  const max = Math.max(1, ...rows.flatMap((r) => cols.map((c) => values[r]?.[c] || 0)));
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="px-2 py-2 text-left text-slate-500">{rowLabel || ""}</th>
            {cols.map((c) => (
              <th key={c} className="px-2 py-2 capitalize text-slate-400">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <td className="whitespace-nowrap px-2 py-1 text-slate-300">{r || "uncategorized"}</td>
              {cols.map((c) => {
                const v = values[r]?.[c] || 0;
                const a = v / max;
                return (
                  <td key={c} className="px-1 py-1">
                    <div
                      className="grid h-10 place-items-center rounded"
                      style={{ background: `rgba(47, 111, 237, ${0.12 + a * 0.75})` }}
                      title={`${r} / ${c}: ${v}`}
                    >
                      {v || ""}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
