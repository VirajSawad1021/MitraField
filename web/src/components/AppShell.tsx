"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { Logo } from "@/components/Logo";

export function AppShell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  const path = usePathname();
  const nav = [
    { href: "/projects", label: "Projects" },
    { href: "/studio", label: "Studio" },
    { href: "/voices", label: "Voices" },
    { href: "/demo", label: "Demo" },
  ];
  return (
    <div className="min-h-screen bg-cream text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-cream/90 backdrop-blur-md">
        <div className={`mx-auto flex h-14 items-center justify-between gap-6 px-5 sm:px-6 ${wide ? "max-w-none" : "max-w-[1240px]"}`}>
          <div className="flex items-center gap-8">
            <Logo />
            <nav className="hidden items-center gap-1 sm:flex">
              {nav.map((n) => (
                <Link key={n.href} href={n.href}
                  className={`rounded-full px-3 py-1.5 text-[13px] transition-colors ${path?.startsWith(n.href) ? "bg-white text-ink shadow-[0_1px_2px_rgba(20,20,19,0.06)]" : "text-body hover:text-ink"}`}>
                  {n.label}
                </Link>
              ))}
            </nav>
          </div>
          <Link href="/new" className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink px-4 text-[13px] font-medium text-white hover:bg-ink-soft">
            <Plus className="h-4 w-4" /> New video
          </Link>
        </div>
      </header>
      {children}
    </div>
  );
}
