import type { ReactNode } from "react";

export function Panel({
  children,
  className = "",
  grid = false,
}: {
  children: ReactNode;
  className?: string;
  grid?: boolean;
}) {
  return (
    <section
      className={`rounded-xl border border-line bg-panel/70 backdrop-blur-sm ${grid ? "cv-grid" : ""} ${className}`}
    >
      {children}
    </section>
  );
}

export function PanelHead({
  title,
  kicker,
  right,
}: {
  title: string;
  kicker?: string;
  right?: ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
      <div>
        {kicker && (
          <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-faint">
            {kicker}
          </div>
        )}
        <h2 className="text-[15px] font-semibold tracking-tight text-ink">{title}</h2>
      </div>
      {right}
    </header>
  );
}

export function Stat({
  value,
  label,
  sub,
  accent,
}: {
  value: ReactNode;
  label: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-panel-2/60 px-4 py-3.5">
      <div
        className="font-mono text-2xl leading-none font-semibold tabular-nums"
        style={{ color: accent ?? "var(--color-ink)" }}
      >
        {value}
      </div>
      <div className="mt-2 text-[11px] font-medium tracking-wide text-muted uppercase">{label}</div>
      {sub && <div className="mt-1 text-[11px] leading-snug text-faint">{sub}</div>}
    </div>
  );
}

export function Pill({
  children,
  accent,
  title,
}: {
  children: ReactNode;
  accent?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[10.5px] tracking-wide whitespace-nowrap"
      style={{
        color: accent ?? "var(--color-muted)",
        borderColor: accent ? `color-mix(in srgb, ${accent} 38%, transparent)` : "var(--color-line)",
        background: accent ? `color-mix(in srgb, ${accent} 11%, transparent)` : "transparent",
      }}
    >
      {children}
    </span>
  );
}

export function Dot({ accent }: { accent: string }) {
  return (
    <span
      className="inline-block size-1.5 shrink-0 rounded-full"
      style={{ background: accent, boxShadow: `0 0 9px ${accent}` }}
    />
  );
}

/** A claim the judges should be able to check, with the command that checks it. */
export function Provenance({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3 border-l-2 border-line-bright pl-3 font-mono text-[11px] leading-relaxed text-faint">
      {children}
    </p>
  );
}
