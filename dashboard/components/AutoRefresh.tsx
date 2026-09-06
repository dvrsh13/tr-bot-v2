"use client";

// Resumed PWA sessions re-validate on focus/visibility: the server component
// re-renders, the flap cascade re-runs, and the ages shown are current again.

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function AutoRefresh() {
  const router = useRouter();
  useEffect(() => {
    const refresh = () => router.refresh();
    const onVis = () => {
      if (document.visibilityState === "visible") refresh();
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [router]);
  return null;
}
