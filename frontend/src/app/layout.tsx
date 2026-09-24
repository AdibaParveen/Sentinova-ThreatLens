import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/lib/auth";

export const metadata: Metadata = {
  title: "ThreatLens — Cyber Threat Intelligence",
  description: "Correlated, scored, and actionable cyber threat intelligence for SOC teams.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
