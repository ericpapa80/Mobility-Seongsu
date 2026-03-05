import { useEffect, useState, type RefObject } from 'react';

/**
 * Returns a counter that increments whenever the observed element resizes.
 * Add the returned value to a useEffect dependency array to re-run
 * D3 draw logic when the container width/height changes.
 */
export function useResizeKey(ref: RefObject<HTMLElement | null>): number {
  const [key, setKey] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new ResizeObserver(() => setKey(k => k + 1));
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref]);

  return key;
}
