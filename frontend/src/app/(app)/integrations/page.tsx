"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { ApiKeyRow, WebhookRow } from "@/lib/types";
import { copyText } from "@/lib/ui";

const EVENTS = ["alerts.stream", "indicators.high_severity", "notifications", "incidents.update"];

export default function IntegrationsPage() {
  const toast = useToast();
  const [secret, setSecret] = useState<string | null>(null);
  const [hookName, setHookName] = useState("");
  const [hookUrl, setHookUrl] = useState("");
  const [events, setEvents] = useState<string[]>(["alerts.stream"]);
  const [hookSecret, setHookSecret] = useState<string | null>(null);

  const keys = useQuery({ queryKey: ["api-keys"], queryFn: () => api<ApiKeyRow[]>("/api/v1/api-keys") });
  const hooks = useQuery({ queryKey: ["webhooks"], queryFn: () => api<WebhookRow[]>("/api/v1/webhooks") });

  return (
    <div>
      <PageHeader title="Integrations" subtitle="API keys and outbound webhooks for automation." />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">API keys</h2>
            <button
              className="btn-primary"
              onClick={async () => {
                try {
                  const r = await api<{ secret: string }>("/api/v1/api-keys", { method: "POST" });
                  setSecret(r.secret);
                  toast("Key created — copy it now");
                  keys.refetch();
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Create failed", "err");
                }
              }}
            >
              Create key
            </button>
          </div>
          {secret && (
            <p className="mb-3 break-all rounded bg-white/5 p-2 font-mono text-xs">
              {secret}{" "}
              <button
                className="btn-ghost ml-2"
                onClick={async () => {
                  toast((await copyText(secret)) ? "Copied" : "Copy failed", "ok");
                }}
              >
                Copy
              </button>
            </p>
          )}
          {keys.isLoading && <Skeleton className="h-24" />}
          {keys.error && <ErrorState message="Unable to load API keys." onRetry={() => keys.refetch()} />}
          {(keys.data || []).length === 0 && !keys.isLoading && <Empty title="No keys yet." />}
          {(keys.data || []).map((k) => (
            <div key={k.id} className="mb-2 flex items-center justify-between rounded bg-white/5 p-2 text-sm">
              <div>
                <p className="font-mono">{k.prefix}…</p>
                <p className="text-xs text-slate-400">
                  {fmt(k.created_at)} · {k.revoked ? "revoked" : "active"}
                </p>
              </div>
              {!k.revoked && (
                <button
                  className="btn-ghost"
                  onClick={async () => {
                    try {
                      await api(`/api/v1/api-keys/${k.id}/revoke`, { method: "POST" });
                      toast("Key revoked");
                      keys.refetch();
                    } catch (e) {
                      toast(e instanceof Error ? e.message : "Revoke failed", "err");
                    }
                  }}
                >
                  Revoke
                </button>
              )}
            </div>
          ))}
        </section>
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Webhooks</h2>
          <input className="input mb-2" placeholder="Name" value={hookName} onChange={(e) => setHookName(e.target.value)} />
          <input className="input mb-2" placeholder="https://…" value={hookUrl} onChange={(e) => setHookUrl(e.target.value)} />
          <div className="mb-3 flex flex-wrap gap-2 text-xs">
            {EVENTS.map((ev) => (
              <label key={ev} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={events.includes(ev)}
                  onChange={(e) => setEvents((s) => (e.target.checked ? [...s, ev] : s.filter((x) => x !== ev)))}
                />
                {ev}
              </label>
            ))}
          </div>
          <button
            className="btn-primary mb-4"
            onClick={async () => {
              if (!hookName.trim() || !hookUrl.trim()) return toast("Name and URL required", "err");
              try {
                const r = await api<{ secret: string }>("/api/v1/webhooks", {
                  method: "POST",
                  body: JSON.stringify({ name: hookName, url: hookUrl, events }),
                });
                setHookSecret(r.secret);
                setHookName("");
                setHookUrl("");
                toast("Webhook created");
                hooks.refetch();
              } catch (e) {
                toast(e instanceof Error ? e.message : "Create failed", "err");
              }
            }}
          >
            Add webhook
          </button>
          {hookSecret && <p className="mb-3 break-all rounded bg-white/5 p-2 font-mono text-xs">Signing secret: {hookSecret}</p>}
          {hooks.isLoading && <Skeleton className="h-24" />}
          {hooks.error && <ErrorState message="Unable to load webhooks." onRetry={() => hooks.refetch()} />}
          {(hooks.data || []).map((w) => (
            <div key={w.id} className="mb-2 rounded bg-white/5 p-2 text-sm">
              <div className="flex justify-between gap-2">
                <div>
                  <p className="font-medium">{w.name}</p>
                  <p className="break-all text-xs text-slate-400">{w.url}</p>
                  <p className="text-xs text-slate-500">{(w.events || []).join(", ")}</p>
                </div>
                <button
                  className="btn-ghost"
                  onClick={async () => {
                    try {
                      await api(`/api/v1/webhooks/${w.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !w.enabled }) });
                      toast(w.enabled ? "Disabled" : "Enabled");
                      hooks.refetch();
                    } catch (e) {
                      toast(e instanceof Error ? e.message : "Update failed", "err");
                    }
                  }}
                >
                  {w.enabled ? "Disable" : "Enable"}
                </button>
              </div>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
