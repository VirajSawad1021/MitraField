"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "light";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink-soft disabled:bg-[#b9b6ae]",
  secondary: "bg-white text-ink border border-line-strong hover:border-ink/40 disabled:text-muted",
  ghost: "text-body hover:text-ink hover:bg-panel-2",
  danger: "bg-white text-bad border border-[#ecd0d0] hover:border-bad",
  light: "bg-white text-ink hover:bg-cream",
};
const sizes: Record<Size, string> = { sm: "h-8 px-3.5 text-[12px]", md: "h-10 px-4.5 text-[13px]", lg: "h-12 px-6 text-[14px]" };
const base =
  "inline-flex items-center justify-center gap-2 rounded-full font-semibold whitespace-nowrap transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100";

export function Button({
  variant = "primary", size = "md", loading, className = "", children, ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size; loading?: boolean }) {
  return (
    <button {...props} disabled={props.disabled || loading} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function LinkButton({
  href, variant = "primary", size = "md", className = "", children,
}: { href: string; variant?: Variant; size?: Size; className?: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  );
}

export function Card({ className = "", children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div {...props} className={`rounded-2xl border border-line bg-white ${className}`}>
      {children}
    </div>
  );
}

export type Tone = "neutral" | "good" | "warn" | "bad" | "info" | "dark" | "ai";
const tones: Record<Tone, string> = {
  neutral: "bg-panel-2 text-body",
  good: "bg-good-bg text-good",
  warn: "bg-warn-bg text-warn",
  bad: "bg-bad-bg text-bad",
  info: "bg-info-bg text-info",
  dark: "bg-ink text-white",
  ai: "bg-[#efe7f6] text-[#6b4f8a]",   // the AI-generated label
};

export function Badge({ tone = "neutral", children, className = "", title }: { tone?: Tone; children: React.ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold whitespace-nowrap ${tones[tone]} ${className}`}>
      {children}
    </span>
  );
}

export const inputCls =
  "w-full rounded-xl border border-line-strong/80 bg-white px-3.5 py-2.5 text-[14px] text-ink placeholder:text-[#aaa79f] transition-colors focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink disabled:bg-panel";

export function Field({ label, hint, children }: { label: string; hint?: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-[12px] font-semibold text-ink">{label}</span>
      {children}
      {hint && <span className="block text-[11px] leading-snug text-muted">{hint}</span>}
    </label>
  );
}

export function Segmented<T extends string>({ value, onChange, options, size = "md" }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: React.ReactNode }[]; size?: "sm" | "md";
}) {
  return (
    <div className="inline-flex rounded-full bg-panel-2 p-1">
      {options.map((o) => (
        <button key={o.value} type="button" onClick={() => onChange(o.value)}
          className={`rounded-full font-medium transition-all ${size === "sm" ? "h-7 px-3 text-[12px]" : "h-8 px-3.5 text-[13px]"} ${o.value === value ? "bg-white text-ink shadow-[0_1px_2px_rgba(20,20,19,0.08)]" : "text-body hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string | null | undefined; onRetry?: () => void }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex items-start justify-between gap-3 rounded-xl border border-[#ecd0d0] bg-bad-bg px-4 py-3 text-[13px] text-bad">
      <span>{message}</span>
      {onRetry && <button onClick={onRetry} className="shrink-0 font-semibold underline underline-offset-2">Retry</button>}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-xl ${className}`} />;
}

/** Shows which agent is working, instead of an anonymous spinner. */
export function AgentWorking({ agent, task }: { agent: string; task: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-panel px-4 py-3 animate-fade-in">
      <span className="relative flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full art-charcoal text-white">
        <Loader2 className="h-4 w-4 animate-spin" />
      </span>
      <div className="min-w-0">
        <p className="text-[13px] font-semibold text-ink">{agent}</p>
        <p className="truncate text-[12px] text-muted">{task}</p>
      </div>
    </div>
  );
}

export function Empty({ title, body, action, icon }: { title: string; body?: string; action?: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-line-strong bg-panel/50 px-6 py-12 text-center">
      {icon && <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-ink shadow-sm">{icon}</div>}
      <p className="text-[16px] font-semibold text-ink">{title}</p>
      {body && <p className="mx-auto mt-1.5 max-w-md text-[13px] leading-relaxed text-body">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Eyebrow({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <p className={`text-[11px] font-semibold uppercase tracking-[0.08em] text-muted ${className}`}>{children}</p>;
}

export const fmtTime = (s?: number | null) =>
  s == null ? "" : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
