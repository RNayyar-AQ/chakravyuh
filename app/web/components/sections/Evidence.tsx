import { LiveVerify } from "@/components/LiveVerify";
import { Panel, PanelHead, Pill } from "@/components/ui";
import type { Bundle } from "@/lib/types";

const STATUS_ACCENT: Record<string, string> = {
  held: "var(--color-pass)",
  partial: "var(--color-block)",
  wanted: "var(--color-fail)",
};

/** Sources, hashes and the chain. The place to doubt everything above it. */
export function Evidence({ b }: { b: Bundle }) {
  return (
    <div className="grid gap-4">
      <Panel className="overflow-hidden">
        <PanelHead
          kicker="data/sources/MANIFEST.yaml"
          title="The documents behind the law, and the ones we do not have"
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-[12.5px]">
            <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Instrument</th>
                <th className="px-4 py-2.5 font-medium">Gazette reference</th>
                <th className="px-4 py-2.5 font-medium">SHA-256</th>
                <th className="px-4 py-2.5 font-medium">Feeds</th>
              </tr>
            </thead>
            <tbody>
              {b.sources.map((s) => (
                <tr key={s.id} className="border-b border-line/50 align-top last:border-0">
                  <td className="px-5 py-3">
                    <Pill accent={STATUS_ACCENT[s.status]}>{s.status}</Pill>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-ink">{s.instrument || s.id}</div>
                    <div className="mt-0.5 font-mono text-[10.5px] text-faint">
                      {s.jurisdiction}
                      {s.pages ? ` · ${s.pages}pp` : ""}
                      {s.official ? " · official" : ""}
                    </div>
                    {s.reason && (
                      <div className="mt-1 text-[11.5px] leading-snug text-block">
                        {Array.isArray(s.reason) ? s.reason.join("; ") : s.reason}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[11.5px] leading-snug text-muted">
                    {s.gazette || "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-[10.5px] text-faint">
                    {s.sha256 ? `${s.sha256}…` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex flex-wrap gap-1">
                      {s.feeds.map((f) => (
                        <Pill key={f}>{f}</Pill>
                      ))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-line px-5 py-4 text-[12.5px] leading-relaxed text-muted">
          A hash proves a file did not change; it does not prove the file is complete. Each source
          therefore also declares strings it must contain. That check caught a composite PDF that
          would have made a missing authentication requirement look like a confirmed absence — the
          exact false negative this project exists to prevent.
        </div>
      </Panel>

      <Panel className="overflow-hidden">
        <PanelHead
          kicker="Y.3172 node SINK"
          title="Hash-chained ledgers, and what happens when one is edited"
          right={
            <span className="hidden font-mono text-[10.5px] text-faint sm:block">
              sha256(prev_hash | seq | t | kind | canonical_json(payload))
            </span>
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[740px] text-left text-[12.5px]">
            <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">Run</th>
                <th className="px-4 py-2.5 font-medium">Entries</th>
                <th className="px-4 py-2.5 font-medium">Head hash</th>
                <th className="px-4 py-2.5 font-medium">Verification</th>
              </tr>
            </thead>
            <tbody>
              {b.ledger.runs.map((r) => (
                <tr key={r.run_id} className="border-b border-line/50 last:border-0">
                  <td className="px-5 py-3 font-mono text-[11px] text-ink">{r.run_id}</td>
                  <td className="px-4 py-3 font-mono tabular-nums text-muted">
                    {r.entries.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-[10.5px] text-faint">
                    {r.head_hash.slice(0, 20)}…
                  </td>
                  <td className="px-4 py-3">
                    <Pill accent={r.verified ? "var(--color-pass)" : "var(--color-fail)"}>
                      {r.verified ? "chain intact" : r.message}
                    </Pill>
                  </td>
                </tr>
              ))}
              {b.ledger.tamper.map((t) => (
                <tr key={t.run_id} className="border-b border-line/50 bg-fail/5 last:border-0">
                  <td className="px-5 py-3 font-mono text-[11px] text-muted">{t.run_id}</td>
                  <td className="px-4 py-3 text-faint">—</td>
                  <td className="px-4 py-3 text-faint">—</td>
                  <td className="px-4 py-3">
                    <Pill accent="var(--color-fail)">{t.message}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <LiveVerify />
      </Panel>
    </div>
  );
}
