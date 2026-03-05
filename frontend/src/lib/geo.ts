import type { GeoJSONCollection } from '../api/client';

export function pointInPolygon(lng: number, lat: number, ring: number[][]): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1];
    const xj = ring[j][0], yj = ring[j][1];
    if ((yi > lat) !== (yj > lat) && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

export interface AreaDef { name: string; ring: number[][] }

export function extractAreas(geoJson: GeoJSONCollection): AreaDef[] {
  return geoJson.features.map(f => {
    const coords = f.geometry.coordinates as number[][][][];
    return { name: f.properties['상권명'] as string, ring: coords[0][0] };
  });
}

export function findArea(lng: number, lat: number, areas: AreaDef[]): string {
  for (const a of areas) {
    if (pointInPolygon(lng, lat, a.ring)) return a.name;
  }
  return '기타';
}

export function polygonCentroid(ring: number[][]): [number, number] {
  let area = 0, cx = 0, cy = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const cross = ring[i][0] * ring[j][1] - ring[j][0] * ring[i][1];
    area += cross;
    cx += (ring[i][0] + ring[j][0]) * cross;
    cy += (ring[i][1] + ring[j][1]) * cross;
  }
  area *= 0.5;
  const f6a = 1 / (6 * area);
  return [cx * f6a, cy * f6a];
}
