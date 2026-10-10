"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Chakra } from "./Chakra";

/** The single page's bands, in the order they are read. */
export const SECTIONS = [
  { id: "live", label: "Run it live" },
  { id: "flow", label: "The flow" },
  { id: "tech", label: "The stack" },
] as const;

function useActiveSection(enabled: boolean): string {
  const [active, setActive] = useState<string>(SECTIONS[0].id);

  useEffect(() => {
    if (!enabled) return;
    const nodes = SECTIONS.map((s) => document.getElementById(s.id)).filter(
      (n): n is HTMLElement => n !== null,
    );
    if (nodes.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-15% 0px -70% 0px", threshold: 0 },
    );
    nodes.forEach((n) => observer.observe(n));
    return () => observer.disconnect();
  }, [enabled]);

  return active;
}

export function Nav() {
  const pathname = usePathname();
  const onePage = pathname === "/";
  const active = useActiveSection(onePage);
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-ground/85 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link href="/" className="flex shrink-0 items-center gap-2.5" onClick={() => setOpen(false)}>
          <Chakra size={26} />
          <span className="font-mono text-[13px] font-semibold tracking-[0.2em] text-ink">
            CHAKRAVYUH
          </span>
        </Link>

        <nav className="ml-auto hidden min-w-0 items-center gap-0.5 overflow-x-auto md:flex">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={onePage ? `#${s.id}` : `/#${s.id}`}
              className={`rounded-md px-2.5 py-1.5 text-[12px] font-medium whitespace-nowrap transition-colors ${
                onePage && active === s.id
                  ? "bg-panel-2 text-ink"
                  : "text-muted hover:bg-panel-2/60 hover:text-ink"
              }`}
            >
              {s.label}
            </a>
          ))}
        </nav>

        <Link
          href="/rubric"
          className={`ml-auto shrink-0 rounded-md border px-3 py-1.5 text-[12px] font-medium transition-colors md:ml-2 ${
            pathname === "/rubric"
              ? "border-line-bright bg-panel-2 text-ink"
              : "border-line text-muted hover:text-ink"
          }`}
        >
          Rubric
        </Link>

        <button
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle navigation"
          aria-expanded={open}
          className="shrink-0 rounded-md border border-line px-2.5 py-1.5 text-muted md:hidden"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
            {open ? <path d="M3 3l10 10M13 3L3 13" /> : <path d="M2 4h12M2 8h12M2 12h12" />}
          </svg>
        </button>
      </div>

      {open && (
        <nav className="grid gap-0.5 border-t border-line px-4 py-3 md:hidden">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={onePage ? `#${s.id}` : `/#${s.id}`}
              onClick={() => setOpen(false)}
              className={`rounded-md px-3 py-2 text-sm ${
                onePage && active === s.id ? "bg-panel-2 text-ink" : "text-muted"
              }`}
            >
              {s.label}
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}
