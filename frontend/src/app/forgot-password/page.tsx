"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Logo } from "@/components/Logo";

export default function Forgot() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <form
        className="panel w-full max-w-md p-6"
        onSubmit={async (e) => {
          e.preventDefault();
          const r = await api<{ message: string }>("/api/v1/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
          setMsg(r.message);
        }}
      >
        <Logo />
        <h1 className="mt-4 text-xl font-semibold">Forgot password</h1>
        <input className="input mt-4" type="email" required placeholder="Work email" value={email} onChange={(e) => setEmail(e.target.value)} />
        {msg && <p className="mt-3 text-sm text-low">{msg}</p>}
        <button className="btn-primary mt-4 w-full">Send reset email</button>
        <Link className="mt-3 block text-center text-sm text-slate-400" href="/login">
          Back to sign in
        </Link>
      </form>
    </div>
  );
}
