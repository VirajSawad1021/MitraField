import { engineStyle } from "@/lib/engines";

/** Soft tinted engine label: tinted fill, coloured icon and text, hairline border. */
export function EngineChip({ engine, label, size = "md" }: { engine: string; label?: string; size?: "sm" | "md" }) {
  const s = engineStyle(engine);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-semibold whitespace-nowrap ${size === "sm" ? "px-2 py-px text-[10.5px]" : "px-2.5 py-0.5 text-[11.5px]"}`}
      style={{ background: `${s.color}14`, borderColor: `${s.color}2e`, color: s.color }}>
      <s.icon className={size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5"} />
      {label ?? s.short}
    </span>
  );
}

/** Square soft tile with the engine icon (for compact lists). */
export function EngineTile({ engine, className = "h-6 w-6", solid = false }: { engine: string; className?: string; solid?: boolean }) {
  const s = engineStyle(engine);
  return (
    <span title={s.short} className={`flex shrink-0 items-center justify-center rounded-lg ${className}`}
      style={solid ? { background: s.color, color: "#fff" } : { background: `${s.color}17`, color: s.color }}>
      <s.icon className="h-[55%] w-[55%]" />
    </span>
  );
}
