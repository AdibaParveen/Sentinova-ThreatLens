"use client";

import { apiUrl, getTokens } from "./api";

export type WsHandler = (msg: { type: string; payload?: unknown }) => void;

export function connectWs(onMessage: WsHandler): () => void {
  const { access } = getTokens();
  if (!access) return () => undefined;
  const wsUrl = apiUrl.replace(/^http/, "ws") + `/api/v1/ws?token=${encodeURIComponent(access)}`;
  let closed = false;
  let ws: WebSocket | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;

  const open = () => {
    if (closed) return;
    ws = new WebSocket(wsUrl);
    ws.onmessage = (ev) => {
      try {
        onMessage(JSON.parse(ev.data));
      } catch {
        /* ignore */
      }
    };
    ws.onopen = () => {
      timer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
      }, 20000);
    };
    ws.onclose = () => {
      if (timer) clearInterval(timer);
      if (!closed) setTimeout(open, 3000);
    };
  };
  open();
  return () => {
    closed = true;
    if (timer) clearInterval(timer);
    ws?.close();
  };
}
