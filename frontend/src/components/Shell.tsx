"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { roleLabel } from "@/lib/format";
import { connectWs } from "@/lib/ws";
import { Logo } from "./Logo";
import { useToast } from "./Toast";

export function Shell({ children }: { children: React.ReactNode }) {
  const { user, navigation, loading, logout } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState<Record<string, unknown> | null>(null);
  const [notes, setNotes] = useState<{ unread: number; items: { id: string; title: string; body: string; read: boolean; link?: string }[] }>({
    unread: 0,
    items: [],
  });
  const [bell, setBell] = useState(false);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    const load = () =>
      api<typeof notes>("/api/v1/notifications").then(setNotes).catch(() => undefined);
    load();
    return connectWs((msg) => {
      if (msg.type === "alerts.stream") toast("New or updated alert");
      if (msg.type === "indicators.high_severity") toast("High-severity indicator");
      if (msg.type === "notifications") load();
      load();
    });
  }, [user, toast]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Loading ThreatLens…
      </div>
    );
  }

  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return;
    const data = await api<Record<string, unknown>>(`/api/v1/search?q=${encodeURIComponent(q)}`);
    setSearch(data);
  };

  return (
    <div className="flex min-h-screen">
      <aside className={`fixed z-30 h-full w-60 border-r border-white/10 bg-navy-900 p-4 transition md:static ${open ? "translate-x-0" : "-translate-x-full md:translate-x-0"}`}>
        <Logo />
        <nav className="mt-6 space-y-1 text-sm">
          {navigation.map((n) => (
            <Link
              key={n.id}
              href={n.href}
              className={`block rounded-md px-3 py-2 ${path.startsWith(n.href) ? "bg-accent/20 text-white" : "text-slate-300 hover:bg-white/5"}`}
              onClick={() => setOpen(false)}
            >
              {n.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-white/10 bg-navy-900/80 px-4 py-3">
          <button className="btn-ghost md:hidden" onClick={() => setOpen((v) => !v)}>
            Menu
          </button>
          <form onSubmit={runSearch} className="relative flex-1">
            <input className="input" placeholder="Search indicators, alerts, incidents, ATT&CK…" value={q} onChange={(e) => setQ(e.target.value)} />
            {search && (
              <div className="absolute z-20 mt-1 max-h-96 w-full overflow-auto rounded-md border border-white/10 bg-navy-800 p-3 text-sm">
                <button className="float-right text-xs" onClick={() => setSearch(null)} type="button">
                  Close
                </button>
                {["indicators", "alerts", "incidents", "events", "techniques", "tags"].map((k) => (
                  <div key={k} className="mb-2">
                    <p className="text-[11px] uppercase text-slate-500">{k}</p>
                    <pre className="whitespace-pre-wrap text-xs text-slate-300">{JSON.stringify((search as Record<string, unknown>)[k], null, 0)}</pre>
                  </div>
                ))}
              </div>
            )}
          </form>
          <button className="relative btn-ghost" onClick={() => setBell((v) => !v)} aria-label="Notifications">
            Bell
            {notes.unread > 0 && (
              <span className="absolute -right-1 -top-1 rounded-full bg-critical px-1.5 text-[10px]">{notes.unread}</span>
            )}
          </button>
          <div className="relative">
            <button className="flex items-center gap-2 btn-ghost" onClick={() => setMenu((v) => !v)}>
              <span className="grid h-8 w-8 place-items-center rounded-full bg-accent/30 text-xs">
                {user.full_name.slice(0, 1)}
              </span>
              <span className="hidden text-left sm:block">
                <span className="block text-sm">{user.full_name}</span>
                <span className="block text-[11px] capitalize text-slate-400">{roleLabel(user.role)}</span>
              </span>
            </button>
            {menu && (
              <div className="absolute right-0 z-20 mt-1 w-48 rounded-md border border-white/10 bg-navy-800 p-2 text-sm">
                <Link className="block rounded px-2 py-1 hover:bg-white/5" href="/settings/profile">
                  Profile
                </Link>
                <Link className="block rounded px-2 py-1 hover:bg-white/5" href="/settings/security">
                  Security
                </Link>
                <button
                  className="block w-full rounded px-2 py-1 text-left hover:bg-white/5"
                  onClick={async () => {
                    await logout();
                    router.replace("/login");
                  }}
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </header>
        {bell && (
          <div className="absolute right-16 top-16 z-20 w-80 rounded-md border border-white/10 bg-navy-800 p-3">
            <div className="mb-2 flex justify-between text-xs">
              <span>Notifications</span>
              <button
                onClick={() => api("/api/v1/notifications/read-all", { method: "POST" }).then(() => api<typeof notes>("/api/v1/notifications").then(setNotes))}
              >
                Mark all read
              </button>
            </div>
            {notes.items.length === 0 && <p className="text-xs text-slate-500">No notifications</p>}
            {notes.items.map((n) => (
              <Link key={n.id} href={n.link || "/soc"} className="mb-2 block rounded bg-white/5 p-2 text-xs" onClick={() => api(`/api/v1/notifications/${n.id}/read`, { method: "POST" })}>
                <p className={n.read ? "text-slate-400" : "font-semibold"}>{n.title}</p>
                <p className="text-slate-400">{n.body}</p>
              </Link>
            ))}
          </div>
        )}
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
