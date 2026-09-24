"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/settings/profile", label: "Profile" },
  { href: "/settings/security", label: "Security" },
];

export function SettingsNav() {
  const path = usePathname();
  return (
    <div className="mb-5 flex gap-2">
      {ITEMS.map((i) => (
        <Link
          key={i.href}
          href={i.href}
          className={`rounded-md px-3 py-1.5 text-sm ${path === i.href ? "bg-accent/20 text-white" : "btn-ghost"}`}
        >
          {i.label}
        </Link>
      ))}
    </div>
  );
}
