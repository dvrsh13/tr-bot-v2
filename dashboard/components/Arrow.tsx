// Authored direction glyphs (no unicode/emoji as icons). One stroke grammar:
// solid board triangles, 8px, currentColor.

export function ArrowUp({ size = 8 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" aria-hidden="true" style={{ display: "inline", verticalAlign: "baseline" }}>
      <path d="M4 1.2 7.4 6.8H0.6Z" fill="currentColor" />
    </svg>
  );
}

export function ArrowDown({ size = 8 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" aria-hidden="true" style={{ display: "inline", verticalAlign: "baseline" }}>
      <path d="M4 6.8 0.6 1.2h6.8Z" fill="currentColor" />
    </svg>
  );
}

export function LampDot() {
  return (
    <svg width={8} height={8} viewBox="0 0 8 8" aria-hidden="true" style={{ display: "inline", marginRight: 7, verticalAlign: "middle" }}>
      <circle cx="4" cy="4" r="3" fill="currentColor" />
    </svg>
  );
}
