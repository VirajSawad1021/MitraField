"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Plus, X } from "lucide-react";
import { Logo } from "@/components/Logo";

const NAV = [
  { href: "/projects", label: "Projects", also: "/studio" },
  { href: "/voices", label: "Voices" },
  { href: "/verify", label: "Verify" },
  { href: "/demo", label: "Examples" },
];

export function AppShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const path = usePathname() ?? "";
  const [open, setOpen] = useState(false);
  const on = (n: (typeof NAV)[number]) => path.startsWith(n.href) || (!!n.also && path.startsWith(n.also));
  return (
    <div className="min-h-screen bg-cream text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-cream/90 backdrop-blur-md">
        <div className={`mx-auto flex h-14 items-center justify-between gap-6 px-5 sm:px-6 ${wide ? "max-w-none" : "max-w-[1240px]"}`}>
          <div className="flex items-center gap-8">
            <Logo />
            <nav className="hidden items-center gap-1 sm:flex">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href}
                  className={`rounded-full px-3 py-1.5 text-[13px] transition-colors ${on(n) ? "bg-white text-ink shadow-[0_1px_2px_rgba(20,20,19,0.06)]" : "text-body hover:text-ink"}`}>
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-1">
            <Link href="/new" className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-4 text-[13px] font-semibold text-white hover:bg-ink-soft">
              <Plus className="h-4 w-4" /> Create video
            </Link>
            <button onClick={() => setOpen(!open)} className="rounded-full p-2 text-ink sm:hidden" aria-label="Menu" aria-expanded={open}>
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
        {open && (
          <nav className="border-t border-line px-5 pb-4 pt-1 sm:hidden">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} onClick={() => setOpen(false)}
                className={`block border-b border-line py-3 text-[15px] last:border-0 ${on(n) ? "font-semibold text-ink" : "text-body"}`}>
                {n.label}
              </Link>
            ))}
          </nav>
        )}
      </header>
      {children}
    </div>
  );
}
