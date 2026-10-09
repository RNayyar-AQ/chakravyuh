"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Chakra } from "./Chakra";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/simulation", label: "Simulation" },
  { href: "/agents", label: "Agents" },
  { href: "/failures", label: "Failure Atlas" },
  { href: "/gaps", label: "Gap Register" },
  { href: "/evidence", label: "Evidence" },
  { href: "/standards", label: "Standards" },
] as const;

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-ground/85 backdrop-blur-xl">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5" onClick={() => setOpen(false)}>
          <Chakra size={26} />
          <span className="font-mono text-[13px] font-semibold tracking-[0.2em] text-ink">
            CHAKRAVYUH
          </span>
        </Link>

        <nav className="ml-auto hidden items-center gap-0.5 lg:flex">
          {LINKS.map((l) => {
            const active = pathname === l.href;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-md px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
                  active ? "bg-panel-2 text-ink" : "text-muted hover:bg-panel-2/60 hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle navigation"
          aria-expanded={open}
          className="ml-auto rounded-md border border-line px-2.5 py-1.5 text-muted lg:hidden"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6">
            {open ? <path d="M3 3l10 10M13 3L3 13" /> : <path d="M2 4h12M2 8h12M2 12h12" />}
          </svg>
        </button>
      </div>

      {open && (
        <nav className="grid gap-0.5 border-t border-line px-4 py-3 lg:hidden">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={`rounded-md px-3 py-2 text-sm ${
                pathname === l.href ? "bg-panel-2 text-ink" : "text-muted"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
