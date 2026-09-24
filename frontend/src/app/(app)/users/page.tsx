"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Empty, ErrorState, Skeleton } from "@/components/States";
import { useToast } from "@/components/Toast";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmt, roleLabel } from "@/lib/format";
import type { Paged, User } from "@/lib/types";
import { ROLES, USER_STATUSES } from "@/lib/ui";

export default function UsersPage() {
  const toast = useToast();
  const { user: me } = useAuth();
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");

  const list = useQuery({
    queryKey: ["users-admin"],
    queryFn: () => api<Paged<User>>("/api/v1/users"),
  });

  const items = useMemo(() => {
    return (list.data?.items || []).filter((u) => {
      if (role && u.role !== role) return false;
      if (status && u.status !== status) return false;
      if (q && !`${u.full_name} ${u.email}`.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [list.data, q, role, status]);

  const patch = async (id: string, body: Record<string, unknown>, ok: string) => {
    try {
      await api(`/api/v1/users/${id}/role`, { method: "PATCH", body: JSON.stringify(body) });
      toast(ok);
      list.refetch();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Update failed", "err");
    }
  };

  return (
    <div>
      <PageHeader title="User administration" subtitle="Roles and account status. Changes are written to the audit log." />
      <div className="mb-4 grid gap-2 md:grid-cols-3">
        <input className="input" placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="">All roles</option>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {roleLabel(r)}
            </option>
          ))}
        </select>
        <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {USER_STATUSES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      {list.isLoading && <Skeleton className="h-64" />}
      {list.error && <ErrorState message="Unable to load users." onRetry={() => list.refetch()} />}
      {!list.isLoading && items.length === 0 && <Empty title="No users match these filters." />}
      <div className="table-wrap panel">
        <table className="data">
          <thead>
            <tr>
              <th>User</th>
              <th>Organization</th>
              <th>Role</th>
              <th>Status</th>
              <th>MFA</th>
              <th>Last login</th>
            </tr>
          </thead>
          <tbody>
            {items.map((u) => (
              <tr key={u.id}>
                <td>
                  <p className="font-medium">{u.full_name}</p>
                  <p className="text-xs text-slate-400">{u.email}</p>
                </td>
                <td className="text-sm">
                  {u.organization}
                  {u.job_title ? <span className="block text-xs text-slate-400">{u.job_title}</span> : null}
                </td>
                <td>
                  <select
                    className="input w-auto"
                    value={u.role}
                    disabled={u.id === me?.id}
                    onChange={(e) => patch(u.id, { role: e.target.value }, "Role updated")}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {roleLabel(r)}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <select
                    className="input w-auto"
                    value={u.status}
                    disabled={u.id === me?.id}
                    onChange={(e) => patch(u.id, { status: e.target.value }, "Status updated")}
                  >
                    {USER_STATUSES.map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </td>
                <td>{u.mfa_enabled ? "on" : "off"}</td>
                <td className="text-xs">{fmt(u.last_login_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
