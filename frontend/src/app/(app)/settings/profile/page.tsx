"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { SettingsNav } from "@/components/SettingsNav";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api, downloadAuthenticated } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, roleLabel } from "@/lib/format";
import type { AuditRow, Preferences } from "@/lib/types";

const NOTE_KEYS: { id: string; label: string }[] = [
  { id: "high_severity", label: "High-severity indicators" },
  { id: "new_incidents", label: "New incidents" },
  { id: "incident_assignments", label: "Incident assignments" },
  { id: "intel_updates", label: "Intelligence updates" },
  { id: "system", label: "System notices" },
  { id: "email", label: "Email delivery" },
  { id: "in_app", label: "In-app bell" },
];

export default function ProfileSettingsPage() {
  const { user, prefs, refreshMe } = useAuth();
  const toast = useToast();
  const qc = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [job, setJob] = useState("");
  const [org, setOrg] = useState("");
  const [picture, setPicture] = useState("");
  const [email, setEmail] = useState("");
  const [theme, setTheme] = useState("dark");
  const [density, setDensity] = useState("comfortable");
  const [dashboard, setDashboard] = useState("soc");
  const [refresh, setRefresh] = useState(15);
  const [notes, setNotes] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name);
    setJob(user.job_title || "");
    setOrg(user.organization || "");
    setPicture(user.profile_picture || "");
  }, [user]);

  useEffect(() => {
    if (!prefs) return;
    setTheme(prefs.theme || "dark");
    setDensity(prefs.density || "comfortable");
    setDashboard(prefs.default_dashboard || "soc");
    setRefresh(prefs.refresh_interval || 15);
    setNotes(prefs.notifications || {});
  }, [prefs]);

  const activity = useQuery({
    queryKey: ["me-activity"],
    queryFn: () => api<AuditRow[]>("/api/v1/me/activity"),
  });

  const saveProfile = useMutation({
    mutationFn: () =>
      api("/api/v1/me", {
        method: "PATCH",
        body: JSON.stringify({ full_name: fullName, job_title: job, organization: org, profile_picture: picture || null }),
      }),
    onSuccess: async () => {
      toast("Profile saved");
      await refreshMe();
    },
    onError: (e: Error) => toast(e.message, "err"),
  });

  const savePrefs = useMutation({
    mutationFn: () =>
      api("/api/v1/me/preferences", {
        method: "PATCH",
        body: JSON.stringify({
          theme,
          density,
          default_dashboard: dashboard,
          refresh_interval: Number(refresh),
          notifications: notes,
        } satisfies Partial<Preferences>),
      }),
    onSuccess: async () => {
      toast("Preferences saved");
      await refreshMe();
      qc.invalidateQueries();
    },
    onError: (e: Error) => toast(e.message, "err"),
  });

  if (!user) return <Skeleton className="h-64" />;

  return (
    <div>
      <PageHeader title="Profile & preferences" subtitle="Identity, notification delivery, and workspace defaults." />
      <SettingsNav />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Account</h2>
          <div className="mb-3 flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-full bg-accent/30 text-lg">{user.full_name.slice(0, 1)}</span>
            <div className="text-sm">
              <p>{user.email}</p>
              <p className="capitalize text-slate-400">
                {roleLabel(user.role)} · {user.status}
                {user.email_verified ? " · verified" : " · email unverified"}
              </p>
            </div>
          </div>
          <label className="mb-2 block text-xs text-slate-400">
            Full name
            <input className="input mt-1" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          </label>
          <label className="mb-2 block text-xs text-slate-400">
            Job title
            <input className="input mt-1" value={job} onChange={(e) => setJob(e.target.value)} />
          </label>
          <label className="mb-2 block text-xs text-slate-400">
            Organization
            <input className="input mt-1" value={org} onChange={(e) => setOrg(e.target.value)} />
          </label>
          <label className="mb-3 block text-xs text-slate-400">
            Profile picture URL
            <input className="input mt-1" value={picture} onChange={(e) => setPicture(e.target.value)} placeholder="https://…" />
          </label>
          <button className="btn-primary" disabled={saveProfile.isPending} onClick={() => saveProfile.mutate()}>
            Save profile
          </button>
        </section>
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Change email</h2>
          <p className="mb-3 text-xs text-slate-400">A verification message is sent to the new address before it replaces the current login.</p>
          <input className="input mb-3" type="email" placeholder="new email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button
            className="btn-ghost"
            onClick={async () => {
              if (!email.trim()) return toast("Enter a new email", "err");
              try {
                await api("/api/v1/me/email", { method: "POST", body: JSON.stringify({ email }) });
                toast("Verification sent");
                setEmail("");
              } catch (e) {
                toast(e instanceof Error ? e.message : "Email change failed", "err");
              }
            }}
          >
            Request change
          </button>
        </section>
        <section className="panel p-4">
          <h2 className="mb-3 text-sm font-semibold">Workspace</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <select className="input" value={theme} onChange={(e) => setTheme(e.target.value)}>
              <option value="dark">Dark theme</option>
              <option value="light">Light theme</option>
            </select>
            <select className="input" value={density} onChange={(e) => setDensity(e.target.value)}>
              <option value="comfortable">Comfortable density</option>
              <option value="compact">Compact density</option>
            </select>
            <select className="input" value={dashboard} onChange={(e) => setDashboard(e.target.value)}>
              <option value="soc">Default: SOC</option>
              <option value="executive">Default: Overview</option>
              <option value="incidents">Default: Incidents</option>
              <option value="hunting">Default: Hunting</option>
            </select>
            <select className="input" value={refresh} onChange={(e) => setRefresh(Number(e.target.value))}>
              <option value={15}>Refresh 15s</option>
              <option value={30}>Refresh 30s</option>
              <option value={60}>Refresh 60s</option>
            </select>
          </div>
          <h3 className="mb-2 mt-4 text-xs uppercase tracking-wide text-slate-500">Notifications</h3>
          <div className="space-y-2">
            {NOTE_KEYS.map((k) => (
              <label key={k.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={notes[k.id] !== false}
                  onChange={(e) => setNotes((s) => ({ ...s, [k.id]: e.target.checked }))}
                />
                {k.label}
              </label>
            ))}
          </div>
          <button className="btn-primary mt-4" disabled={savePrefs.isPending} onClick={() => savePrefs.mutate()}>
            Save preferences
          </button>
        </section>
        <section className="panel p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent activity</h2>
            <button
              className="btn-ghost"
              onClick={async () => {
                try {
                  await downloadAuthenticated("/api/v1/me/export", "threatlens-profile.json");
                  toast("Export downloaded");
                } catch (e) {
                  toast(e instanceof Error ? e.message : "Export failed", "err");
                }
              }}
            >
              Export my data
            </button>
          </div>
          {activity.isLoading && <Skeleton className="h-32" />}
          {activity.error && <ErrorState message="Unable to load activity." onRetry={() => activity.refetch()} />}
          {!activity.isLoading && !(activity.data || []).length && <Empty title="No activity yet." />}
          <ul className="max-h-80 space-y-2 overflow-auto text-xs">
            {(activity.data || []).map((r) => (
              <li key={r.id} className="rounded bg-white/5 p-2">
                <p className="font-medium">{r.action}</p>
                <p className="text-slate-400">
                  {fmt(r.timestamp)} · {r.resource}
                  {r.ip_address ? ` · ${r.ip_address}` : ""}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
