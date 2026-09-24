
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Logo } from "@/components/Logo";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { homePath } from "@/lib/format";

const DEMO_PASSWORD = "ThreatLens!Demo1";

const DEMO_ACCOUNTS = [
  {
    email: "analyst@threatlens.local",
    name: "SOC Analyst",
    role: "SOC Analyst",
    description: "Monitor alerts, incidents and security events.",
  },
  {
    email: "hunter@threatlens.local",
    name: "Threat Hunter",
    role: "Threat Hunter",
    description: "Investigate indicators and perform threat hunting.",
  },
  {
    email: "responder@threatlens.local",
    name: "Incident Responder",
    role: "Incident Responder",
    description: "Investigate and manage security incidents.",
  },
  {
    email: "engineer@threatlens.local",
    name: "Security Engineer",
    role: "Security Engineer",
    description: "Manage detection engineering and security controls.",
  },
  {
    email: "admin@threatlens.local",
    name: "Administrator",
    role: "Administrator",
    description: "Full platform administration access.",
  },
  {
    email: "exec@threatlens.local",
    name: "Executive",
    role: "Executive",
    description: "Executive security overview and reporting.",
  },
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const [remember, setRemember] = useState(true);
  const [totp, setTotp] = useState("");
  const [mfa, setMfa] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedAccount =
    DEMO_ACCOUNTS.find((account) => account.email === email) ||
    DEMO_ACCOUNTS[0];

  const selectDemoAccount = (account: (typeof DEMO_ACCOUNTS)[number]) => {
    setEmail(account.email);
    setPassword(DEMO_PASSWORD);
    setError("");
    setMfa(false);
    setTotp("");
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const result = await login(
        email,
        password,
        remember,
        mfa ? totp : undefined
      );

      if (result.mfa) {
        setMfa(true);
        setLoading(false);
        return;
      }

      router.replace(
        homePath(result.preferences?.default_dashboard)
      );
    } catch (ex) {
      if (ex instanceof ApiError) {
        setError(ex.message);
      } else {
        setError("Unable to sign in. Please check the backend connection.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#070b14] text-white">
      <div className="grid min-h-screen lg:grid-cols-2">

        {/* LEFT SIDE */}
        <section className="relative hidden overflow-hidden lg:flex lg:flex-col bg-[radial-gradient(circle_at_25%_20%,#243354,transparent_45%),#070b14] p-12">

          <div className="relative z-10">
            <Logo />
          </div>

          <div className="relative z-10 mt-auto max-w-xl pb-10">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1 text-xs text-cyan-300">
              <span className="h-2 w-2 rounded-full bg-cyan-400" />
              SECURITY OPERATIONS CENTER
            </div>

            <h1 className="text-5xl font-semibold tracking-tight">
              ThreatLens
            </h1>

            <p className="mt-4 text-lg leading-8 text-slate-400">
              Intelligence ingestion, threat detection, incident response,
              correlation and analyst workflows in one controlled security
              operations platform.
            </p>

            <div className="mt-8 grid grid-cols-3 gap-3">
              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
                <p className="text-xl font-semibold">SOC</p>
                <p className="mt-1 text-xs text-slate-500">
                  Operations
                </p>
              </div>

              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
                <p className="text-xl font-semibold">TI</p>
                <p className="mt-1 text-xs text-slate-500">
                  Intelligence
                </p>
              </div>

              <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
                <p className="text-xl font-semibold">IR</p>
                <p className="mt-1 text-xs text-slate-500">
                  Response
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT SIDE */}
        <section className="flex items-center justify-center p-6 sm:p-10">
          <div className="w-full max-w-2xl">

            <div className="mb-8 lg:hidden">
              <Logo />
            </div>

            <div className="mb-6">
              <div className="mb-3 inline-flex items-center rounded-full border border-cyan-400/20 bg-cyan-400/5 px-3 py-1 text-xs font-medium text-cyan-300">
                DEMO ENVIRONMENT
              </div>

              <h2 className="text-3xl font-semibold tracking-tight">
                Welcome to ThreatLens
              </h2>

              <p className="mt-2 text-sm text-slate-400">
                Select a demo role below to explore the platform.
              </p>
            </div>

            {/* DEMO ACCOUNTS */}
            <div className="grid gap-3 sm:grid-cols-2">
              {DEMO_ACCOUNTS.map((account) => {
                const selected = account.email === email;

                return (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => selectDemoAccount(account)}
                    className={`rounded-xl border p-4 text-left transition ${
                      selected
                        ? "border-cyan-400/50 bg-cyan-400/10"
                        : "border-white/10 bg-white/[0.03] hover:border-white/20 hover:bg-white/[0.05]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">
                          {account.name}
                        </p>

                        <p className="mt-1 text-xs text-cyan-300">
                          {account.role}
                        </p>
                      </div>

                      {selected && (
                        <span className="rounded-full bg-cyan-400/10 px-2 py-1 text-[10px] text-cyan-300">
                          SELECTED
                        </span>
                      )}
                    </div>

                    <p className="mt-3 text-xs leading-5 text-slate-500">
                      {account.description}
                    </p>
                  </button>
                );
              })}
            </div>

            {/* LOGIN PANEL */}
            <form
              onSubmit={handleLogin}
              className="panel mt-6 w-full p-6"
            >
              <div className="mb-5">
                <p className="text-xs uppercase tracking-wider text-slate-500">
                  Selected demo account
                </p>

                <p className="mt-1 font-medium">
                  {selectedAccount.name}
                </p>

                <p className="mt-1 font-mono text-xs text-slate-500">
                  {selectedAccount.email}
                </p>
              </div>

              <label className="block text-sm">
                Demo email
              </label>

              <input
                className="input mt-1"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />

              <label className="mt-4 block text-sm">
                Demo password
              </label>

              <input
                className="input mt-1"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              {mfa && (
                <div className="mt-4">
                  <label className="block text-sm">
                    Authenticator code
                  </label>

                  <input
                    className="input mt-1"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={totp}
                    onChange={(e) => setTotp(e.target.value)}
                    placeholder="Enter 6-digit code"
                  />
                </div>
              )}

              <label className="mt-4 flex items-center gap-2 text-sm text-slate-400">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                Remember this demo session
              </label>

              {error && (
                <div className="mt-4 rounded-lg border border-critical/30 bg-critical/10 p-3 text-sm text-critical">
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="btn-primary mt-5 w-full"
                disabled={loading}
              >
                {loading ? "Connecting to ThreatLens…" : "Enter Demo SOC"}
              </button>

              <div className="mt-5 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                <p className="text-[11px] text-slate-500">
                  Demo password
                </p>

                <p className="mt-1 font-mono text-xs text-slate-300">
                  {DEMO_PASSWORD}
                </p>
              </div>
            </form>

            <p className="mt-6 text-center text-[11px] text-slate-600">
              ThreatLens Demo Environment · Authentication and RBAC remain
              enabled.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

