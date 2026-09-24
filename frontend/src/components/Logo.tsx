export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="6" fill="#0b1220" />
        <path d="M16 4l10 4v8c0 6.2-4.2 11.6-10 13-5.8-1.4-10-6.8-10-13V8l10-4z" fill="#2f6fed" />
        <circle cx="16" cy="16" r="3.2" fill="#0b1220" />
      </svg>
      {!compact && (
        <span className="text-sm font-semibold tracking-wide">
          Threat<span className="text-accent">Lens</span>
        </span>
      )}
    </div>
  );
}
