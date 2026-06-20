import { useCallback, useEffect, useRef, useState } from "react";

export interface ResizablePanelOptions {
  initial: number;
  min: number;
  max: number;
  /** localStorage key to persist the width across sessions. */
  storageKey?: string;
  /**
   * Which edge the drag handle sits on, relative to the panel:
   *  - "right": handle on the panel's right edge (a LEFT sidebar) → width grows
   *    as the pointer moves right.
   *  - "left": handle on the panel's left edge (a RIGHT panel) → width grows as
   *    the pointer moves left.
   */
  edge: "left" | "right";
}

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

/**
 * Pointer-driven, rAF-throttled panel resizing with localStorage persistence.
 * Mirrors the resizer mechanics used on the Repository Explorer page so the two
 * workspaces feel identical.
 */
export function useResizablePanel({ initial, min, max, storageKey, edge }: ResizablePanelOptions) {
  const [width, setWidth] = useState<number>(initial);
  const [isDragging, setIsDragging] = useState(false);

  const startXRef = useRef(0);
  const startWidthRef = useRef(initial);
  const rafRef = useRef<number | null>(null);

  // Load persisted width once.
  useEffect(() => {
    if (!storageKey) return;
    try {
      const saved = window.localStorage.getItem(storageKey);
      if (saved) setWidth(clamp(Number(saved), min, max));
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist on change.
  useEffect(() => {
    if (!storageKey) return;
    try {
      window.localStorage.setItem(storageKey, String(width));
    } catch {
      /* ignore */
    }
  }, [width, storageKey]);

  const onResizerPointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      try {
        (e.target as Element).setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
      startXRef.current = e.clientX;
      startWidthRef.current = width;
      setIsDragging(true);

      const onMove = (ev: PointerEvent) => {
        const delta = ev.clientX - startXRef.current;
        const dx = edge === "right" ? delta : -delta;
        const next = clamp(startWidthRef.current + dx, min, max);
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        rafRef.current = requestAnimationFrame(() => setWidth(next));
      };

      const onUp = (ev: PointerEvent) => {
        setIsDragging(false);
        try {
          (ev.target as Element).releasePointerCapture(ev.pointerId);
        } catch {
          /* ignore */
        }
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
      };

      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
    },
    [width, edge, min, max]
  );

  return { width, setWidth, isDragging, onResizerPointerDown, clampWidth: (w: number) => clamp(w, min, max) };
}
