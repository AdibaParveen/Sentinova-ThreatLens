"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { Indicator } from "@/lib/types";
import { SeverityBadge } from "./States";
import { useToast } from "./Toast";

export function IndicatorDrawer({
  id,
  onClose,
  onChanged,
}: {
  id: string;
  onClose: () => void;
  onChanged?: () => void;
}) {
  const toast = useToast();
  const q = useQuery({ queryKey: ["ind", id], queryFn: () => api<Indicator>(`/api/v1/indicators/${id}`) });
  const [triage, setTriage] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const ind = q.data;
  const enrich = (ind?.enrichment || {}) as Record<string, unknown>;
  const geo = (enrich.geo || {}) as Record<string, string>;

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label);
    try {
      await fn();
      toast(`${label} complete`);
      q.refetch();
      onChanged?.();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed", "err");
    } finally {
      setBusy("");
    }
  };

  const breakdown = useMemo(() => ind?.score_breakdown, [ind]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/40">
      <button className="h-full flex-1" onClick={onClose} aria-label="Close drawer" />
      <aside className="h-full w-full max-w-xl overflow-y-auto border-l border-white/10 bg-navy-900 p-5">
        {q.isLoading && <p className="text-sm text-slate-400">Loading indicator…</p>}
        {q.error && <p className="text-sm text-critical">Unable to load indicator.</p>}
        {ind && (
          <>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-mono text-sm text-accent">{ind.value}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <SeverityBadge value={ind.severity} />
                  <span className="rounded bg-white/5 px-2 py-0.5 text-xs uppercase">{ind.type}</span>
                  <span className="rounded bg-white/5 px-2 py-0.5 text-xs">TLP:{ind.tlp}</span>
                  <span className="rounded bg-white/5 px-2 py-0.5 text-xs">{ind.status}</span>
                </div>
              </div>
              <button className="btn-ghost" onClick={onClose}>
                Close
              </button>
            </div>

            <section className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <Field label="Severity score" value={`${ind.severity_score}/100`} />
              <Field label="Confidence" value={`${ind.confidence}%`} />
              <Field label="First seen" value={fmt(ind.first_seen)} />
              <Field label="Last seen" value={fmt(ind.last_seen)} />
              <Field label="Category" value={ind.category} />
              <Field label="Status" value={ind.status} />
            </section>

            {breakdown && (
              <section className="mt-5 panel p-3">
                <h3 className="text-xs font-semibold uppercase text-slate-400">Score breakdown</h3>
                <div className="mt-2 h-2 overflow-hidden rounded bg-white/10">
                  <div className="h-full bg-accent" style={{ width: `${ind.severity_score}%` }} />
                </div>
                <ul className="mt-2 space-y-1 text-xs text-slate-300">
                  {Object.entries(breakdown.weights).map(([k, w]) => (
                    <li key={k} className="flex justify-between">
                      <span>{k.replaceAll("_", " ")}</span>
                      <span>{Math.round(w * 100)}%</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <section className="mt-5">
              <h3 className="text-xs font-semibold uppercase text-slate-400">Reputation / provenance</h3>
              <div className="mt-2 space-y-1">
                {(ind.sources || []).map((s, i) => (
                  <div key={i} className="flex justify-between rounded bg-white/5 px-2 py-1 text-xs">
                    <span>{s.name}</span>
                    <span>
                      {s.verdict} · {s.confidence}%
                    </span>
                  </div>
                ))}
                {!ind.sources?.length && <p className="text-xs text-slate-500">Insufficient evidence available.</p>}
              </div>
            </section>

            {ind.type === "ip" && (
              <section className="mt-5 grid grid-cols-2 gap-2 text-sm">
                <Field label="Country" value={ind.country || geo.country || "—"} />
                <Field label="City" value={ind.city || geo.city || "—"} />
                <Field label="ISP" value={geo.isp || "—"} />
                <Field label="ASN" value={geo.asn || "—"} />
                <Field label="Org" value={geo.org || "—"} />
              </section>
            )}

            {String(ind.type).startsWith("hash") && (
              <section className="mt-5 text-sm">
                <Field label="Malware family" value={ind.malware_family || String(enrich.malware_family || "—")} />
                <p className="mt-2 text-xs text-slate-400">Detection engines</p>
                <ul className="mt-1 text-xs">
                  {((enrich.engines as { name: string; result: string }[]) || []).map((e) => (
                    <li key={e.name}>
                      {e.name}: {e.result}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(ind.type === "domain" || ind.type === "url") && (
              <section className="mt-5 text-sm">
                <Field label="Phishing" value={String(enrich.phishing ?? "Insufficient evidence available.")} />
              </section>
            )}

            <section className="mt-5">
              <h3 className="text-xs font-semibold uppercase text-slate-400">ATT&CK</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {(ind.attack || []).map((t) => (
                  <span key={t.id} className="rounded border border-white/10 px-2 py-1 text-xs">
                    {t.id} {t.name}
                  </span>
                ))}
                {!ind.attack?.length && <p className="text-xs text-slate-500">Insufficient evidence available.</p>}
              </div>
            </section>

            <section className="mt-5">
              <h3 className="text-xs font-semibold uppercase text-slate-400">Internal correlation</h3>
              {(ind.internal_events || []).map((e) => (
                <p key={e.id} className="mt-1 text-xs text-slate-300">
                  {fmt(e.occurred_at)} · {e.type} · {e.source_host} · {e.user || "n/a"}
                </p>
              ))}
              {!ind.internal_events?.length && <p className="text-xs text-slate-500">No internal sightings.</p>}
            </section>

            <div className="mt-5 flex flex-wrap gap-2">
              <button className="btn-primary" disabled={!!busy} onClick={() => run("Enrich", () => api(`/api/v1/indicators/${id}/enrich`, { method: "POST" }))}>
                {busy === "Enrich" ? "Enriching…" : "Enrich"}
              </button>
              <button
                className="btn-ghost"
                disabled={!!busy}
                onClick={() =>
                  run("AI triage", async () => {
                    const s = await api<Record<string, unknown>>(`/api/v1/indicators/${id}/ai-triage`, { method: "POST" });
                    setTriage(s);
                  })
                }
              >
                AI Triage Summary
              </button>
              <select
                className="input w-auto"
                value={ind.status}
                onChange={(e) => run("Status", () => api(`/api/v1/indicators/${id}`, { method: "PATCH", body: JSON.stringify({ status: e.target.value }) }))}
              >
                {["active", "expired", "whitelisted", "under_review"].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="mt-3 flex gap-2">
              <input className="input" placeholder="Add analyst note" value={note} onChange={(e) => setNote(e.target.value)} />
              <button
                className="btn-ghost"
                onClick={() =>
                  run("Note", () => api(`/api/v1/indicators/${id}`, { method: "PATCH", body: JSON.stringify({ notes: note }) }))
                }
              >
                Save note
              </button>
            </div>

            {triage && (
              <section className="mt-5 panel p-4">
                <h3 className="text-sm font-semibold">Why this matters</h3>
                <p className="mt-2 text-sm text-slate-300">{String(triage.why)}</p>
                <h4 className="mt-3 text-xs font-semibold uppercase text-slate-400">Evidence</h4>
                <pre className="mt-1 overflow-x-auto text-xs text-slate-400">{JSON.stringify(triage.evidence, null, 2)}</pre>
                <h4 className="mt-3 text-xs font-semibold uppercase text-slate-400">Suggested investigation steps</h4>
                <ul className="mt-1 list-disc pl-4 text-sm">
                  {((triage.steps as string[]) || []).map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
                <p className="mt-3 text-[11px] text-slate-500">
                  Generated at {String(triage.generated_at)} · Data used: {((triage.data_used as string[]) || []).join(", ")}
                </p>
                <p className="text-[11px] text-amber-300">{String(triage.disclaimer)}</p>
              </section>
            )}
          </>
        )}
      </aside>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase text-slate-500">{label}</p>
      <p>{value}</p>
    </div>
  );
}
