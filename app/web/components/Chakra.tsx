/**
 * The chakravyuh: concentric rings of a labyrinth formation, each turning at its own rate.
 * It is the project's namesake and also, literally, its architecture — an outer ring of agents,
 * an inner ring of rules, and a fixed centre that decides.
 */
export function Chakra({ size = 40, spin = true }: { size?: number; spin?: boolean }) {
  const rings = [
    { r: 46, dash: "10 7", w: 1.6, dur: 48, rev: false, o: 0.85 },
    { r: 35, dash: "5 9", w: 1.3, dur: 32, rev: true, o: 0.65 },
    { r: 25, dash: "3 6", w: 1.1, dur: 22, rev: false, o: 0.5 },
  ];
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden className="shrink-0">
      <defs>
        <radialGradient id="cv-core">
          <stop offset="0%" stopColor="#ffb08a" />
          <stop offset="100%" stopColor="var(--color-brand)" />
        </radialGradient>
      </defs>
      {rings.map((ring, i) => (
        <circle
          key={i}
          cx="50"
          cy="50"
          r={ring.r}
          fill="none"
          stroke="var(--color-brand)"
          strokeWidth={ring.w}
          strokeDasharray={ring.dash}
          opacity={ring.o}
          style={
            spin
              ? {
                  transformOrigin: "50% 50%",
                  animation: `${ring.rev ? "cv-spin-rev" : "cv-spin"} ${ring.dur}s linear infinite`,
                }
              : undefined
          }
        />
      ))}
      {/* The centre never moves: the policy engine is a pure function. */}
      <circle cx="50" cy="50" r="11" fill="url(#cv-core)" />
      <circle cx="50" cy="50" r="11" fill="none" stroke="#ffd9c7" strokeWidth="0.8" opacity="0.5" />
    </svg>
  );
}
