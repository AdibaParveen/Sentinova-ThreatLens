export function severityClass(sev: string) {
  const s = (sev || "").toLowerCase();
  if (s === "critical") return "text-critical bg-critical/15 border-critical/40";
  if (s === "high") return "text-high bg-high/15 border-high/40";
  if (s === "medium") return "text-yellow-200 bg-yellow-500/10 border-yellow-500/30";
  return "text-low bg-low/15 border-low/40";
}

export function fmt(ts?: string | null) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString();
}

export function roleLabel(role: string) {
  return role.replaceAll("_", " ");
}

export function homePath(dashboard?: string | null) {
  const d = (dashboard || "soc").toLowerCase();
  if (d === "executive" || d === "overview") return "/overview";
  if (d === "hunting") return "/hunting";
  if (d === "incidents") return "/incidents";
  if (d.startsWith("/")) return d;
  return "/soc";
}
