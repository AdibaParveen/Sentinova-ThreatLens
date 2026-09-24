export function SeverityBadge({ value }: { value: string }) {
  const s = (value || "low").toLowerCase();
  const cls =
    s === "critical"
      ? "bg-critical/15 text-critical"
      : s === "high"
        ? "bg-high/15 text-high"
        : s === "medium"
          ? "bg-yellow-500/15 text-yellow-200"
          : "bg-low/15 text-low";
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${cls}`}>{s}</span>;
}

export function Skeleton({ className = "h-24" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-white/5 ${className}`} />;
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="panel p-8 text-center text-slate-400">
      <p className="font-medium text-slate-200">{title}</p>
      {hint && <p className="mt-1 text-sm">{hint}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="panel p-6">
      <p className="text-sm text-critical">{message}</p>
      {onRetry && (
        <button className="btn-primary mt-3" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
