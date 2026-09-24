const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function cid() {
  return crypto.randomUUID();
}

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getTokens() {
  if (typeof window === "undefined") return { access: null as string | null, refresh: null as string | null };
  return {
    access: sessionStorage.getItem("tl_access") || localStorage.getItem("tl_access"),
    refresh: localStorage.getItem("tl_refresh"),
  };
}

export function setTokens(access: string, refresh?: string, remember = true) {
  sessionStorage.setItem("tl_access", access);
  if (remember) localStorage.setItem("tl_access", access);
  if (refresh) localStorage.setItem("tl_refresh", refresh);
}

export function clearTokens() {
  sessionStorage.removeItem("tl_access");
  localStorage.removeItem("tl_access");
  localStorage.removeItem("tl_refresh");
}

async function tryRefresh(): Promise<string | null> {
  const refresh = localStorage.getItem("tl_refresh");
  if (!refresh) return null;
  const res = await fetch(`${API}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  setTokens(data.access_token);
  return data.access_token as string;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Correlation-ID", cid());
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const { access } = getTokens();
  if (access) headers.set("Authorization", `Bearer ${access}`);
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (res.status === 401 && retry) {
    const next = await tryRefresh();
    if (next) return api<T>(path, init, false);
  }
  if (!res.ok) {
    let message = res.statusText;
    let code: string | undefined;
    try {
      const body = await res.json();
      const d = body.detail;
      if (typeof d === "string") message = d;
      else if (d?.message) {
        message = d.message;
        code = d.error_code;
      } else if (body.message) message = body.message;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, message, code);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/pdf") || ct.includes("text/csv")) {
    return (await res.blob()) as T;
  }
  return res.json();
}

export const apiUrl = API;

export async function downloadAuthenticated(path: string, filename: string) {
  const headers = new Headers();
  headers.set("X-Correlation-ID", cid());
  let { access } = getTokens();
  if (access) headers.set("Authorization", `Bearer ${access}`);
  let res = await fetch(`${API}${path}`, { headers });
  if (res.status === 401) {
    const next = await tryRefresh();
    if (next) {
      headers.set("Authorization", `Bearer ${next}`);
      res = await fetch(`${API}${path}`, { headers });
    }
  }
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const ct = res.headers.get("content-type") || "";
  let blob: Blob;
  if (ct.includes("application/json")) {
    const data = await res.json();
    blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  } else {
    blob = await res.blob();
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
