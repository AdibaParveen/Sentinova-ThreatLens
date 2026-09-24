"use client";

import Link from "next/link";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const [form, setForm] = useState({ full_name: "", email: "", password: "", confirm_password: "", organization: "", job_title: "" });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const set = (k: string, v: string) => setForm((s) => ({ ...s, [k]: v }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const r = await api<{ message: string }>("/api/v1/auth/register", { method: "POST", body: JSON.stringify(form) });
      setMsg(r.message);
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={submit} className="panel w-full max-w-lg p-6">
        <Logo />
        <h1 className="mt-4 text-xl font-semibold">Create account</h1>
        <p className="text-sm text-slate-400">New users receive SOC Analyst access after email verification. Admins are never auto-granted.</p>
        {["full_name", "email", "organization", "job_title"].map((k) => (
          <div key={k} className="mt-3">
            <label className="text-sm capitalize">{k.replace("_", " ")}</label>
            <input className="input mt-1" required={k === "full_name" || k === "email"} type={k === "email" ? "email" : "text"} onChange={(e) => set(k, e.target.value)} />
          </div>
        ))}
        <label className="mt-3 block text-sm">Password</label>
        <input className="input mt-1" type="password" required onChange={(e) => set("password", e.target.value)} />
        <label className="mt-3 block text-sm">Confirm password</label>
        <input className="input mt-1" type="password" required onChange={(e) => set("confirm_password", e.target.value)} />
        <ul className="mt-3 list-disc pl-5 text-xs text-slate-400">
          <li>At least 12 characters</li>
          <li>Uppercase, lowercase, number, and symbol</li>
        </ul>
        {err && <p className="mt-3 text-sm text-critical">{err}</p>}
        {msg && <p className="mt-3 text-sm text-low">{msg}</p>}
        <button className="btn-primary mt-4 w-full" disabled={loading}>
          {loading ? "Submitting…" : "Create Account"}
        </button>
        <Link className="mt-3 block text-center text-sm text-slate-400" href="/login">
          Back to sign in
        </Link>
      </form>
    </div>
  );
}
