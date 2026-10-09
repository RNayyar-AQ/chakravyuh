"use client";

import { useEffect, useMemo, useState } from "react";

import { RunFooterPanel } from "@/components/RunFooterPanel";
import { Dot, Panel, Pill } from "@/components/ui";
import {
  DECISION_ACCENT,
  PACK_ACCENT,
  ROLE_ACCENT,
  ROLE_SHORT,
  istClock,
  tPlus,
} from "@/lib/format";
import type { Pack, Timeline, TimelineItem } from "@/lib/types";

const KINDS = ["EVENT", "PROPOSAL", "EFFECT", "PROPERTY"] as const;
const PAGE = 120;

interface PackView {
  pack: string;
  data: Timeline | null;
  error: string;
  limit: number;
  open: number | null;
}

const EMPTY_VIEW = { data: null, error: "", limit: PAGE, open: null } as const;

/** The default view hides repetitive ALLOWs: a judge wants the refusals and the consequences. */
function isSignificant(i: TimelineItem): boolean {
  if (i.kind !== "PROPOSAL") return true;
  if (i.action === "NOOP") return false;
  return i.decision !== "ALLOW";
}

export function TimelineExplorer({ packs }: { packs: Pack[] }) {
  const [packId, setPackId] = useState(packs[0]?.pack_id ?? "india_current");
  const [showAll, setShowAll] = useState(false);
  const [kinds, setKinds] = useState<string[]>([...KINDS]);
  const [role, setRole] = useState("");
  const [query, setQuery] = useState("");

  // Everything that belongs to ONE pack's ledger is held together and tagged with that pack, so
  // switching regime resets it during render rather than through an effect that fires a second
  // pass with the previous pack's rows still on screen. Filters live outside, and persist.
  const [view, setView] = useState<PackView>({ pack: packId, ...EMPTY_VIEW });
  const v: PackView = view.pack === packId ? view : { pack: packId, ...EMPTY_VIEW };
  const { data, error, limit, open } = v;

  useEffect(() => {
    let live = true;
    fetch(`/data/timeline.${packId}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((d: Timeline) => live && setView({ pack: packId, ...EMPTY_VIEW, data: d }))
      .catch((e: Error) => live && setView({ pack: packId, ...EMPTY_VIEW, error: e.message }));
    return () => {
      live = false;
    };
  }, [packId]);

  const roles = useMemo(() => {
    const s = new Set<string>();
    data?.items.forEach((i) => i.role && s.add(i.role));
    return [...s].sort();
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.items.filter((i) => {
      if (!kinds.includes(i.kind)) return false;
      if (!showAll && !isSignificant(i)) return false;
      if (role && i.role !== role) return false;
      if (!q) return true;
      return JSON.stringify(i).toLowerCase().includes(q);
    });
  }, [data, kinds, showAll, role, query]);

  const horizon = (data?.header.horizon_min as number) ?? 7500;

  return (
    <div className="grid gap-4">
      {/* regime selector */}
      <div className="flex flex-wrap gap-2">
        {packs.map((p) => {
          const active = p.pack_id === packId;
          return (
            <button
              key={p.pack_id}
              onClick={() => setPackId(p.pack_id)}
              className="rounded-lg border px-4 py-2 text-left transition-colors"
              style={{
                borderColor: active
                  ? `color-mix(in srgb, ${PACK_ACCENT[p.pack_id]} 52%, transparent)`
                  : "var(--color-line)",
                background: active
                  ? `color-mix(in srgb, ${PACK_ACCENT[p.pack_id]} 11%, transparent)`
                  : "transparent",
              }}
            >
              <div className="flex items-center gap-2">
                <Dot accent={PACK_ACCENT[p.pack_id]} />
                <span
                  className="font-mono text-[12.5px] font-semibold"
                  style={{ color: active ? PACK_ACCENT[p.pack_id] : "var(--color-muted)" }}
                >
                  {p.label}
                </span>
              </div>
              <div className="mt-0.5 text-[10.5px] text-faint">{p.rule_count} rules · {p.mode}</div>
            </button>
          );
        })}
      </div>

      {error && (
        <Panel className="p-5 text-[13px] text-fail">
          Could not load the timeline for {packId}: {error}. Run{" "}
          <code className="font-mono">python scripts/export_web.py</code> first.
        </Panel>
      )}

      {!data && !error && (
        <Panel className="p-10 text-center">
          <div className="font-mono text-[12px] text-faint" style={{ animation: "cv-pulse 1.4s ease-in-out infinite" }}>
            loading ledger…
          </div>
        </Panel>
      )}

      {data && (
        <>
          {/* run summary */}
          <Panel className="p-4">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <div className="font-mono text-[11px] text-faint">
                <span className="text-muted">run</span> {data.run_id}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(data.decisions).map(([d, n]) => (
                  <Pill key={d} accent={DECISION_ACCENT[d]}>
                    {d} {n}
                  </Pill>
                ))}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(data.counts).map(([k, n]) => (
                  <Pill key={k}>
                    {k} {n}
                  </Pill>
                ))}
              </div>
            </div>

            {/* decision density over the scenario clock */}
            <div className="relative mt-4 h-10 overflow-hidden rounded-md border border-line bg-ground/60">
              {data.items
                .filter((i) => i.kind === "PROPOSAL" && i.decision && i.decision !== "ALLOW")
                .map((i) => (
                  <span
                    key={i.seq}
                    className="absolute top-0 h-full w-px"
                    style={{
                      left: `${Math.min(100, (i.t / horizon) * 100)}%`,
                      background: DECISION_ACCENT[i.decision!],
                      opacity: 0.5,
                    }}
                  />
                ))}
              {data.items
                .filter((i) => i.kind === "EVENT")
                .map((i) => (
                  <span
                    key={`e${i.seq}`}
                    title={i.event_type}
                    className="absolute top-0 h-full w-0.5"
                    style={{ left: `${Math.min(100, (i.t / horizon) * 100)}%`, background: "#ffffff66" }}
                  />
                ))}
              <span className="absolute bottom-0.5 left-2 font-mono text-[9px] text-faint">T+0</span>
              <span className="absolute right-2 bottom-0.5 font-mono text-[9px] text-faint">
                {tPlus(horizon)}
              </span>
            </div>
            <div className="mt-2 font-mono text-[10px] text-faint">
              white = incoming event · coloured = a proposal the rulebook refused or escalated
            </div>
          </Panel>

          {data.footer && <RunFooterPanel footer={data.footer} />}

          {/* filters */}
          <Panel className="flex flex-wrap items-center gap-3 p-3.5">
            <div className="flex flex-wrap gap-1.5">
              {KINDS.map((k) => {
                const on = kinds.includes(k);
                return (
                  <button
                    key={k}
                    onClick={() =>
                      setKinds((prev) => (on ? prev.filter((x) => x !== k) : [...prev, k]))
                    }
                    className={`rounded-md border px-2.5 py-1 font-mono text-[10.5px] transition-colors ${
                      on
                        ? "border-line-bright bg-panel-2 text-ink"
                        : "border-line text-faint hover:text-muted"
                    }`}
                  >
                    {k}
                  </button>
                );
              })}
            </div>

            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="rounded-md border border-line bg-panel-2 px-2.5 py-1.5 font-mono text-[11px] text-ink"
            >
              <option value="">all roles</option>
              {roles.map((r) => (
                <option key={r} value={r}>
                  {ROLE_SHORT[r] ?? r}
                </option>
              ))}
            </select>

            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="search clause id, area, action…"
              className="min-w-[200px] flex-1 rounded-md border border-line bg-panel-2 px-3 py-1.5 font-mono text-[11px] text-ink placeholder:text-faint"
            />

            <label className="flex cursor-pointer items-center gap-2 font-mono text-[10.5px] text-muted">
              <input
                type="checkbox"
                checked={showAll}
                onChange={(e) => setShowAll(e.target.checked)}
                className="accent-[var(--color-brand)]"
              />
              show routine ALLOWs
            </label>

            <span className="ml-auto font-mono text-[10.5px] text-faint">
              {filtered.length.toLocaleString()} / {data.items.length.toLocaleString()}
            </span>
          </Panel>

          {/* the log */}
          <Panel className="divide-y divide-line">
            {filtered.slice(0, limit).map((i) => (
              <Row key={i.seq} item={i} open={open === i.seq} onToggle={() => setView({ ...v, open: open === i.seq ? null : i.seq })} />
            ))}
            {filtered.length === 0 && (
              <div className="px-5 py-10 text-center text-[12.5px] text-faint">
                Nothing matches these filters.
              </div>
            )}
            {filtered.length > limit && (
              <button
                onClick={() => setView({ ...v, limit: limit + PAGE * 4 })}
                className="w-full px-5 py-3.5 font-mono text-[11.5px] text-muted transition-colors hover:bg-panel-2 hover:text-ink"
              >
                show {Math.min(PAGE * 4, filtered.length - limit).toLocaleString()} more of{" "}
                {(filtered.length - limit).toLocaleString()} remaining ↓
              </button>
            )}
          </Panel>
        </>
      )}
    </div>
  );
}

function Row({ item, open, onToggle }: { item: TimelineItem; open: boolean; onToggle: () => void }) {
  const accent =
    item.kind === "PROPOSAL"
      ? (DECISION_ACCENT[item.decision ?? ""] ?? "var(--color-faint)")
      : item.kind === "EVENT"
        ? "#ffffff"
        : item.kind === "EFFECT"
          ? "var(--color-allow)"
          : item.holds
            ? "var(--color-pass)"
            : "var(--color-fail)";

  return (
    <div>
      <button onClick={onToggle} className="flex w-full items-start gap-3 px-4 py-2.5 text-left hover:bg-panel-2/60">
        <span className="mt-0.5 w-[112px] shrink-0 font-mono text-[10.5px] text-faint tabular-nums">
          {tPlus(item.t)}
        </span>
        <span className="mt-1 shrink-0">
          <Dot accent={accent} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            {item.kind === "PROPOSAL" && (
              <>
                <span
                  className="font-mono text-[11px] font-semibold"
                  style={{ color: ROLE_ACCENT[item.role ?? ""] ?? "var(--color-muted)" }}
                >
                  {ROLE_SHORT[item.role ?? ""] ?? item.role}
                </span>
                <span className="font-mono text-[12px] text-ink">{item.action}</span>
                {item.params?.area ? (
                  <span className="font-mono text-[10.5px] text-faint">{String(item.params.area)}</span>
                ) : null}
                {item.decision && (
                  <Pill accent={DECISION_ACCENT[item.decision]}>{item.decision}</Pill>
                )}
              </>
            )}
            {item.kind === "EVENT" && (
              <>
                <Pill>EVENT</Pill>
                <span className="font-mono text-[12px] text-ink">{item.event_type}</span>
                {item.area && <span className="font-mono text-[10.5px] text-faint">{item.area}</span>}
                {item.synthetic && <Pill accent="var(--color-human)">synthetic</Pill>}
                {item.claimed_issuer && (
                  <Pill accent="var(--color-fail)">claims to be {item.claimed_issuer}</Pill>
                )}
                {item.authentic === false && (
                  <Pill accent="var(--color-fail)">unauthenticated</Pill>
                )}
              </>
            )}
            {item.kind === "EFFECT" && (
              <>
                <Pill accent="var(--color-allow)">EFFECT</Pill>
                <span className="font-mono text-[12px] text-ink">{item.action}</span>
                {item.area && <span className="font-mono text-[10.5px] text-faint">{item.area}</span>}
                {item.cap_language && (
                  <Pill accent="var(--color-us)">CAP lang {item.cap_language}</Pill>
                )}
              </>
            )}
            {item.kind === "PROPERTY" && (
              <>
                <Pill accent={item.holds ? "var(--color-pass)" : "var(--color-fail)"}>
                  {item.property_id} {item.holds ? "HOLDS" : "VIOLATED"}
                </Pill>
                <span className="text-[12px] text-muted">{item.description}</span>
                {item.margin !== undefined && (
                  <span className="font-mono text-[11px] text-ink tabular-nums">
                    margin {item.margin}
                  </span>
                )}
              </>
            )}
          </span>
          {item.explanation && !open && (
            <span className="mt-1 block truncate font-mono text-[10.5px] text-faint">
              {item.explanation}
            </span>
          )}
        </span>
        <span className="mt-0.5 shrink-0 font-mono text-[10px] text-faint">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="border-t border-line bg-ground/50 px-4 py-4 pl-[136px]">
          <dl className="grid gap-2.5 text-[12px]">
            <Field label="scenario clock">{istClock(item.t)}</Field>
            {item.reasoning && <Field label="stated reasoning">{item.reasoning}</Field>}
            {item.explanation && <Field label="engine explanation">{item.explanation}</Field>}
            {item.rule_ids?.length ? (
              <Field label="cited by the agent">
                <Ids ids={item.rule_ids} />
              </Field>
            ) : null}
            {item.verdict_rule_ids?.length ? (
              <Field label="rules the engine applied">
                <Ids ids={item.verdict_rule_ids} />
              </Field>
            ) : null}
            {(item.verdict_clause_ids?.length || item.clause_ids?.length) ? (
              <Field label="clauses behind the decision">
                <Ids ids={item.verdict_clause_ids?.length ? item.verdict_clause_ids : item.clause_ids!} />
              </Field>
            ) : null}
            {item.params && Object.keys(item.params).length > 0 && (
              <Field label="parameters">
                <Code value={item.params} />
              </Field>
            )}
            {item.payload && Object.keys(item.payload).length > 0 && (
              <Field label="payload">
                <Code value={item.payload} />
              </Field>
            )}
            {item.detail && Object.keys(item.detail).length > 0 && (
              <Field label="world effect">
                <Code value={item.detail} />
              </Field>
            )}
            <Field label="ledger sequence">#{item.seq}</Field>
          </dl>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[150px_1fr] sm:gap-3">
      <dt className="font-mono text-[10px] tracking-wider text-faint uppercase">{label}</dt>
      <dd className="leading-relaxed text-muted">{children}</dd>
    </div>
  );
}

function Ids({ ids }: { ids: string[] }) {
  return (
    <span className="flex flex-wrap gap-1.5">
      {ids.map((id) => (
        <Pill key={id} accent="var(--color-us)">
          {id}
        </Pill>
      ))}
    </span>
  );
}

function Code({ value }: { value: unknown }) {
  return (
    <pre className="overflow-x-auto rounded-md border border-line bg-ground/70 p-2.5 font-mono text-[10.5px] leading-relaxed text-muted">
      {JSON.stringify(value, null, 1)}
    </pre>
  );
}
