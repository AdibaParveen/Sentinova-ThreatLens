"use client";

import { Shell } from "@/components/Shell";
import { ToastHost } from "@/components/Toast";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ToastHost>
      <Shell>{children}</Shell>
    </ToastHost>
  );
}
