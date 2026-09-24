"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Logo } from "@/components/Logo";

function Inner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState("working");
  const [msg, setMsg] = useState("Verifying…");
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("missing");
      setMsg("This page expects a verification link from your email.");
      return;
    }
    api<{ status: string }>(`/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`, { method: "POST" })
      .then((r) => {
        setStatus(r.status);
        setMsg(r.status === "already_verified" ? "This address is already verified." : "Email verified. You can sign in.");
      })
      .catch((e) => {
        setStatus("error");
        setMsg(e instanceof ApiError ? e.message : "Verification failed");
      });
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="panel max-w-md p-6">
        <Logo />
        <h1 className="mt-4 text-xl font-semibold">Email verification</h1>
        <p className="mt-2 text-sm text-slate-300">{msg}</p>
        {status === "error" && (
          <form
            className="mt-4"
            onSubmit={async (e) => {
              e.preventDefault();
              await api("/api/v1/auth/resend-verification", { method: "POST", body: JSON.stringify({ email }) });
              setMsg("If the account needs verification, a new email has been sent.");
            }}
          >
            <input className="input" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button className="btn-primary mt-2 w-full">Resend verification email</button>
          </form>
        )}
        <Link className="btn-ghost mt-4 inline-flex" href="/login">
          Sign In
        </Link>
      </div>
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
