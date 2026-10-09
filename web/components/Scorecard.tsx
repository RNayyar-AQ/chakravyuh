import { PACK_ACCENT, packOrder, signed } from "@/lib/format";
import type { Pack, PropertyResult } from "@/lib/types";

/**
 * Margins are not all in the same unit, and pretending they were would be the exact kind of
 * false precision this project exists to catch. Each property declares its own.
 */
const UNITS: Record<string, { unit: string; meaning: string }> = {
  P1: { unit: "pp", meaning: "percentage points of relief-reachable cells above the 60% floor" },
  P2: { unit: "exec", meaning: "forged orders that executed, against a ceiling of zero" },
  P3: { unit: "min", meaning: "minutes of slack before the 6-hour alert deadline" },
  P4: { unit: "min", meaning: "minutes of slack before the 6-hour disaster-roaming deadline" },
};

export function Scorecard({
  properties,
  packs,
}: {
  properties: PropertyResult[];
  packs: Pack[];
}) {
  const ordered = [...packs].sort((a, b) => packOrder(a.pack_id, b.pack_id));

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] border-collapse text-left">
        <thead>
          <tr>
            <th className="w-[46%] px-5 py-3 text-[10px] font-medium tracking-[0.18em] text-faint uppercase">
              Safety property
            </th>
            {ordered.map((p) => (
              <th key={p.pack_id} className="px-4 py-3">
                <div
                  className="font-mono text-[12px] font-semibold tracking-wide"
                  style={{ color: PACK_ACCENT[p.pack_id] }}
                >
                  {p.label}
                </div>
                <div className="mt-0.5 text-[10.5px] leading-tight font-normal text-faint">
                  {p.rule_count} rules · {p.mode}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {properties.map((prop) => {
            const u = UNITS[prop.property_id];
            return (
              <tr key={prop.property_id} className="border-t border-line align-top">
                <td className="px-5 py-4">
                  <div className="flex items-baseline gap-2.5">
                    <span className="font-mono text-[12px] font-semibold text-brand">
                      {prop.property_id}
                    </span>
                    <span className="text-[13px] leading-snug text-ink">{prop.text}</span>
                  </div>
                  {u && (
                    <div className="mt-1.5 pl-9 text-[11px] leading-snug text-faint">
                      margin in {u.meaning}
                    </div>
                  )}
                </td>
                {ordered.map((pack) => {
                  const margin = prop.margins[pack.pack_id];
                  const pass = prop.passes_under.includes(pack.pack_id);
                  const accent = pass ? "var(--color-pass)" : "var(--color-fail)";
                  return (
                    <td key={pack.pack_id} className="px-4 py-4">
                      <div
                        className="rounded-lg border px-3 py-2.5"
                        style={{
                          borderColor: `color-mix(in srgb, ${accent} 34%, transparent)`,
                          background: `color-mix(in srgb, ${accent} 9%, transparent)`,
                        }}
                      >
                        <div
                          className="font-mono text-[11px] font-bold tracking-[0.14em]"
                          style={{ color: accent }}
                        >
                          {pass ? "PASS" : "FAIL"}
                        </div>
                        <div className="mt-1 font-mono text-[15px] tabular-nums text-ink">
                          {margin === undefined ? "—" : signed(margin)}
                          <span className="ml-1 text-[10px] text-faint">{u?.unit}</span>
                        </div>
                      </div>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
