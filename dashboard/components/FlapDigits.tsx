"use client";

// Flap digits: split-flap cascade (the signature interaction). Each cell rolls
// through glyphs for a bounded number of steps, then settles on its target —
// regardless of the target's membership in the roll alphabet. Static under
// prefers-reduced-motion.

import { useEffect, useRef, useState } from "react";

const ROLL = "0123456789: ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export function FlapDigits({ value, className }: { value: string; className?: string }) {
  const chars = value.split("");
  const [settled, setSettled] = useState(false);
  const prev = useRef(value);
  const reduced = useRef(
    typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    if (prev.current !== value) {
      prev.current = value;
      setSettled(false);
      const t = setTimeout(() => setSettled(true), chars.length * 60 + 8 * 45 + 150);
      return () => clearTimeout(t);
    }
    setSettled(true);
  }, [value, chars.length]);

  return (
    <span className={`flap ${className ?? ""}`} aria-label={value}>
      {chars.map((c, i) => (
        <span key={i} className="flap-cell" aria-hidden="true">
          <FlapCell char={c} delay={i * 60} animate={!settled && !reduced.current} />
        </span>
      ))}
    </span>
  );
}

function FlapCell({ char, delay, animate }: { char: string; delay: number; animate: boolean }) {
  const [shown, setShown] = useState(char);

  useEffect(() => {
    if (!animate) {
      setShown(char);
      return;
    }
    const steps = 4 + (delay / 60) % 4; // bounded roll, then settle
    let i = 0;
    const start = setTimeout(() => {
      const iv = setInterval(() => {
        i += 1;
        if (i >= steps) {
          setShown(char);
          clearInterval(iv);
        } else {
          const next = ROLL[Math.floor(Math.random() * ROLL.length)];
          setShown(next === char ? ROLL[(ROLL.indexOf(char) + 7) % ROLL.length] : next);
        }
      }, 45);
    }, delay);
    return () => clearTimeout(start);
  }, [char, animate, delay]);

  return <span className="flap-glyph">{shown}</span>;
}
