import Link from "next/link";

/** Mark: two figures joined into an m (mitra means friend), white on a dark tile. Same image as the favicon. */
export function Logo({ href = "/", className = "" }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={`inline-flex items-center gap-2 ${className}`} aria-label="MitraField home">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo.png" alt="" width={28} height={28} className="h-7 w-7 rounded-[9px]" />
      <span className="text-[17px] font-semibold tracking-tight text-ink">mitrafield</span>
    </Link>
  );
}
