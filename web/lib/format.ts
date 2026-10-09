import type { PackId } from "./types";

/** T+ minutes from the first IMD message, rendered the way an operations log renders it. */
export function tPlus(minutes: number): string {
  const sign = minutes < 0 ? "-" : "+";
  const m = Math.abs(minutes);
  const d = Math.floor(m / 1440);
  const h = Math.floor((m % 1440) / 60);
  const mm = m % 60;
  const hhmm = `${String(h).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
  return d > 0 ? `T${sign}${d}d ${hhmm}` : `T${sign}${hhmm}`;
}

/** Scenario clock -> real IST wall time. T+0 = 16 May 2020, 08:45 IST (the first IMD message). */
export function istClock(minutes: number): string {
  const base = Date.UTC(2020, 4, 16, 3, 15); // 08:45 IST == 03:15 UTC
  const d = new Date(base + minutes * 60_000 + 5.5 * 3600_000);
  const day = d.getUTCDate();
  const month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][d.getUTCMonth()];
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${day} ${month} ${hh}:${mm} IST`;
}

/** Margins are minutes for timing properties and percentage points / counts for the others. */
export function signed(n: number): string {
  return `${n > 0 ? "+" : ""}${Number.isInteger(n) ? n : n.toFixed(1)}`;
}

export const PACK_ACCENT: Record<string, string> = {
  india_current: "var(--color-india)",
  bangladesh: "var(--color-bangladesh)",
  fcc_mdri: "var(--color-us)",
};

export const PACK_SHORT: Record<string, string> = {
  india_current: "India",
  bangladesh: "Bangladesh",
  fcc_mdri: "United States",
};

export const PACK_FLAG: Record<string, string> = {
  india_current: "IN",
  bangladesh: "BD",
  fcc_mdri: "US",
};

export function packOrder(a: string, b: string): number {
  const rank: Record<string, number> = { india_current: 0, bangladesh: 1, fcc_mdri: 2 };
  return (rank[a] ?? 9) - (rank[b] ?? 9);
}

export const ROLE_ACCENT: Record<string, string> = {
  competent_authority: "#f0b429",
  sdma_alerts: "#4aa8ff",
  tsp_network: "#2dd4a7",
  cert_in: "#fb7185",
  neighbour_authority: "#c084fc",
  adviser: "#8597ad",
};

export const ROLE_SHORT: Record<string, string> = {
  competent_authority: "Authority",
  sdma_alerts: "SDMA",
  tsp_network: "TSP NOC",
  cert_in: "CERT-In",
  neighbour_authority: "Neighbour",
  adviser: "Adviser",
};

export const DECISION_ACCENT: Record<string, string> = {
  ALLOW: "var(--color-allow)",
  BLOCK: "var(--color-block)",
  NEEDS_HUMAN: "var(--color-human)",
};

export function isPackId(s: string): s is PackId {
  return s === "india_current" || s === "bangladesh" || s === "fcc_mdri";
}
