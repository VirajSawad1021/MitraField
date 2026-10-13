import Link from "next/link";

/** Mark: a dark tile with a lowercase m and a clay "focus" dot (the beat being routed). */
export function Logo({ href = "/", className = "" }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={`inline-flex items-center gap-2 ${className}`} aria-label="MitraField home">
      <span className="relative flex h-7 w-7 items-center justify-center rounded-[9px] bg-ink text-white">
        <span className="text-[15px] font-semibold leading-none tracking-tight">m</span>
        <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-cream bg-clay" />
      </span>
      <span className="text-[17px] font-semibold tracking-tight text-ink">mitrafield</span>
    </Link>
  );
}
