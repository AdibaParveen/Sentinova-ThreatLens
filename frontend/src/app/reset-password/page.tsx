"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Logo } from "@/components/Logo";

function Inner() {
  const token = useSearchParams().get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form
        className="panel w-full max-w-md p-6"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr("");
          try {
            await api("/api/v1/auth/reset-password", {
              method: "POST",
              body: JSON.stringify({ token, password, confirm_password: confirm }),
            });
            setMsg("Password reset. You can sign in.");
          } catch (ex) {
            setErr(ex instanceof ApiError ? ex.message : "Reset failed");
          }
        }}
      >
        <Logo />
        <h1 className="mt-4 text-xl font-semibold">Reset password</h1>
        <ul className="mt-2 list-disc pl-5 text-xs text-slate-400">
          <li>At least 12 characters with mixed case, number, and symbol</li>
        </ul>
        <input className="input mt-4" type="password" placeholder="New password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <input className="input mt-3" type="password" placeholder="Confirm password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        {err && <p className="mt-2 text-sm text-critical">{err}</p>}
        {msg && <p className="mt-2 text-sm text-low">{msg}</p>}
        <button className="btn-primary mt-4 w-full">Reset password</button>
        <Link className="mt-3 block text-center text-sm text-slate-400" href="/login">
          Sign In
        </Link>
      </form>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense>
      <Inner />
    </Suspense>
  );
}
