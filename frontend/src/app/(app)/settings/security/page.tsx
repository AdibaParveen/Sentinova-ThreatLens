"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { SettingsNav } from "@/components/SettingsNav";
import { ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt } from "@/lib/format";
import type { SessionRow } from "@/lib/types";
import { copyText } from "@/lib/ui";

export default function SecuritySettingsPage() {
  const { user, refreshMe } = useAuth();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [code, setCode] = useState("");
  const [setup, setSetup] = useState<{ secret: string; otpauth_url: string } | null>(null);

  const sessions = useQuery({
    queryKey: ["sessions"],
    queryFn: () => api<SessionRow[]>("/api/v1/me/sessions"),
  });

  const changePassword = async () => {
    try {
      await api("/api/v1/me/password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next, confirm_password: confirm }),
      });
      toast("Password updated");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Password change failed", "err");
    }
  };

  return (
    <div>
      <PageHeader title="Security settings" subtitle="Password, authenticator MFA, and session control." />
      <SettingsNav />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Change password</h2>
          <input className="input mb-2" type="password" placeholder="Current password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          <input className="input mb-2" type="password" placeholder="New password" value={next} onChange={(e) => setNext(e.target.value)} />
          <input className="input mb-3" type="password" placeholder="Confirm new password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          <button className="btn-primary" onClick={changePassword}>
            Update password
          </button>
        </section>
        <section className="panel p-4">
          <h2 className="mb-2 text-sm font-semibold">Multi-factor authentication</h2>
          <p className="mb-3 text-xs text-slate-400">
            Status: {user?.mfa_enabled ? "enabled" : "disabled"}. Add a TOTP authenticator, then confirm a 6-digit code.
          </p>
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              className="btn-ghost"
              onClick={async () => {
                try {
                  const data = await api<{ secret: string; otpauth_url: string }>("/api/v1/auth/mfa/setup", { method: "POST" });
                  setSetup(data);
                  toast("Secret generated");
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Setup failed", "err");
                }
              }}
            >
              Generate secret
            </button>
            <button
              className="btn-primary"
              onClick={async () => {
                try {
                  await api("/api/v1/auth/mfa/enable", { method: "POST", body: JSON.stringify({ code }) });
                  toast("MFA enabled");
                  setCode("");
                  await refreshMe();
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Enable failed", "err");
                }
              }}
            >
              Enable
            </button>
            <button
              className="btn-ghost"
              onClick={async () => {
                try {
                  await api("/api/v1/auth/mfa/disable", { method: "POST", body: JSON.stringify({ code }) });
                  toast("MFA disabled");
                  setSetup(null);
                  setCode("");
                  await refreshMe();
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Disable failed", "err");
                }
              }}
            >
              Disable
            </button>
          </div>
          <input className="input" placeholder="Authenticator code" value={code} onChange={(e) => setCode(e.target.value)} />
          {setup && (
            <div className="mt-3 rounded bg-white/5 p-3 text-xs">
              <p className="mb-1 font-medium">Manual key</p>
              <p className="break-all font-mono">{setup.secret}</p>
              <p className="mb-1 mt-2 font-medium">otpauth URL</p>
              <p className="break-all font-mono text-slate-400">{setup.otpauth_url}</p>
              <button
                className="btn-ghost mt-2"
                onClick={async () => {
                  const ok = await copyText(setup.otpauth_url);
                  toast(ok ? "Copied" : "Copy failed", ok ? "ok" : "err");
                }}
              >
                Copy otpauth URL
              </button>
            </div>
          )}
        </section>
        <section className="panel p-4 lg:col-span-2">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">Sessions</h2>
            <button
              className="btn-ghost"
              onClick={async () => {
                try {
                  await api("/api/v1/me/sessions/revoke-others", { method: "POST" });
                  toast("Other sessions revoked");
                  sessions.refetch();
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Revoke failed", "err");
                }
              }}
            >
              Revoke other sessions
            </button>
          </div>
          {sessions.isLoading && <Skeleton className="h-32" />}
          {sessions.error && <ErrorState message="Unable to load sessions." onRetry={() => sessions.refetch()} />}
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Created</th>
                  <th>Last seen</th>
                  <th>IP</th>
                  <th>User agent</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {(sessions.data || []).map((s) => (
                  <tr key={s.id}>
                    <td>{fmt(s.created_at)}</td>
                    <td>{fmt(s.last_seen_at)}</td>
                    <td className="font-mono text-xs">{s.ip_address || "—"}</td>
                    <td className="max-w-xs truncate text-xs text-slate-400">{s.user_agent || "—"}</td>
                    <td>{s.revoked ? "revoked" : "active"}</td>
                    <td>
                      {!s.revoked && (
                        <button
                          className="btn-ghost"
                          onClick={async () => {
                            try {
                              await api(`/api/v1/sessions/${s.id}/revoke`, { method: "POST" });
                              toast("Session revoked");
                              sessions.refetch();
                            } catch (e) {
                              toast(e instanceof Error ? e.message : "Revoke failed", "err");
                            }
                          }}
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
