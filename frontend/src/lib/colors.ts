import type { Color } from '@deck.gl/core';

export function vcColor(vc: number): Color {
  if (vc >= 1.0) return [153, 27, 27, 200];
  if (vc >= 0.8) return [239, 68, 68, 200];
  if (vc >= 0.5) return [245, 158, 11, 200];
  return [16, 185, 129, 200];
}

export function busMarkerColor(ride: number, alight: number): Color {
  const total = ride + alight;
  if (total === 0) return [100, 116, 139, 160];
  const ratio = ride / total;
  if (ratio > 0.6) return [6, 182, 212, 200];   // cyan — ride dominant
  if (ratio < 0.4) return [236, 72, 153, 200];   // pink — alight dominant
  return [59, 130, 246, 200];                     // blue — balanced
}

export function busMarkerRadius(total: number, hour: number): number {
  const peak = hour >= 7 && hour <= 9 || hour >= 17 && hour <= 19;
  const base = Math.sqrt(total) * 1.0;
  return Math.max(peak ? base * 1.2 : base, 12);
}
