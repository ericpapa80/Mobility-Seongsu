import { useMemo } from 'react';
import type { MapViewState } from '@deck.gl/core';
import type { Store, FoottrafficResponse, BusStopHourlyFull } from '../api/client';
import type { LayerVisibility, FoottrafficSettings, StoreSettings } from './Sidebar';
import type { AreaDef } from '../lib/geo';
import { findArea } from '../lib/geo';
import type { DrillState } from './StoreDrillChart';

interface Props {
  areas: { position: [number, number]; name: string }[];
  areaDefs: AreaDef[];
  viewState: MapViewState;
  layerVisibility: LayerVisibility;
  stores: Store[];
  storeSettings: StoreSettings;
  foottrafficData: FoottrafficResponse | null;
  foottrafficSettings: FoottrafficSettings;
  busStopsFull: BusStopHourlyFull[];
  drillState?: DrillState;
}

const CAT_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};

const SUB_COLORS = [
  '#f59e0b', '#10b981', '#a78bfa', '#22d3ee', '#f87171',
  '#84cc16', '#fb923c', '#60a5fa', '#e879f9', '#94a3b8',
];

function projectLngLat(lng: number, lat: number, vs: MapViewState, containerW: number, containerH: number): [number, number] {
  const scale = 256 * Math.pow(2, vs.zoom);
  const lam = (lng / 360 + 0.5) * scale;
  const phi = (0.5 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / (2 * Math.PI)) * scale;
  const cLam = (vs.longitude / 360 + 0.5) * scale;
  const cPhi = (0.5 - Math.log(Math.tan(Math.PI / 4 + (vs.latitude * Math.PI) / 360)) / (2 * Math.PI)) * scale;
  return [lam - cLam + containerW / 2, phi - cPhi + containerH / 2];
}

interface DonutSlice { key: string; value: number; color: string }

function MiniDonut({ slices, size }: { slices: DonutSlice[]; size: number }) {
  const total = slices.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;
  const r = size / 2;
  const ir = r * 0.45;
  let cumAngle = -Math.PI / 2;

  // peco_total is in 만원; 10,000만 = 1억
  const fmtTotal = (v: number) => {
    if (v >= 10000) return Math.round(v / 10000) + '억';
    return String(Math.round(v));
  };

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {slices.map(d => {
        const angle = (d.value / total) * 2 * Math.PI;
        const startAngle = cumAngle;
        cumAngle += angle;
        const endAngle = cumAngle;
        const largeArc = angle > Math.PI ? 1 : 0;
        const x1 = r + r * Math.cos(startAngle);
        const y1 = r + r * Math.sin(startAngle);
        const x2 = r + r * Math.cos(endAngle);
        const y2 = r + r * Math.sin(endAngle);
        const ix1 = r + ir * Math.cos(startAngle);
        const iy1 = r + ir * Math.sin(startAngle);
        const ix2 = r + ir * Math.cos(endAngle);
        const iy2 = r + ir * Math.sin(endAngle);
        const path = `M${x1},${y1} A${r},${r} 0 ${largeArc},1 ${x2},${y2} L${ix2},${iy2} A${ir},${ir} 0 ${largeArc},0 ${ix1},${iy1} Z`;
        return <path key={d.key} d={path} fill={d.color} opacity={0.85} />;
      })}
      <text x={r} y={r} textAnchor="middle" dominantBaseline="central"
        fill="#e2e8f0" fontSize={size * 0.2} fontWeight={700} fontFamily="'JetBrains Mono', monospace">
        {fmtTotal(total)}
      </text>
    </svg>
  );
}

function MiniSparkline({ values, color, size }: { values: number[]; color: string; size: number }) {
  if (values.length === 0) return null;
  const max = Math.max(...values, 1);
  const h = size * 0.6;
  const w = size;
  const step = w / Math.max(values.length - 1, 1);
  const points = values.map((v, i) => `${i * step},${h - (v / max) * h}`).join(' ');
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} opacity={0.9} />
    </svg>
  );
}

function MiniStackBar({ ride, alight, width }: { ride: number; alight: number; width: number }) {
  const total = ride + alight;
  if (total === 0) return null;
  const rw = (ride / total) * width;
  return (
    <svg width={width} height={10}>
      <rect x={0} y={0} width={rw} height={10} fill="#3b82f6" rx={2} opacity={0.85} />
      <rect x={rw} y={0} width={width - rw} height={10} fill="#ef4444" rx={2} opacity={0.85} />
    </svg>
  );
}

export default function MiniAreaChart({ areas, areaDefs, viewState, layerVisibility: lv, stores, storeSettings, foottrafficData, foottrafficSettings, busStopsFull, drillState }: Props) {
  const chartType = useMemo<'donut' | 'sparkline' | 'bus' | 'none'>(() => {
    if (lv.store) return 'donut';
    if (lv.foottraffic && foottrafficData) return 'sparkline';
    if (lv.bus && busStopsFull.length > 0) return 'bus';
    return 'none';
  }, [lv.store, lv.foottraffic, lv.bus, foottrafficData, busStopsFull.length]);

  // Determine whether to show category_mi breakdown (when drilling into a category)
  const drillCategory = drillState?.level === 'category' || drillState?.level === 'area-grid'
    ? drillState.category
    : undefined;

  const storeByArea = useMemo(() => {
    if (chartType !== 'donut') return new Map<string, DonutSlice[]>();
    const filtered = stores.filter(s => {
      if (!storeSettings.categories.includes(s.category_bg)) return false;
      if (drillCategory && s.category_bg !== drillCategory) return false;
      return true;
    });
    const map = new Map<string, Map<string, number>>();
    for (const s of filtered) {
      const area = findArea(s.lng, s.lat, areaDefs);
      if (area === '기타') continue;
      if (!map.has(area)) map.set(area, new Map());
      const catMap = map.get(area)!;
      const key = drillCategory ? s.category_mi : s.category_bg;
      catMap.set(key, (catMap.get(key) ?? 0) + s.peco_total);
    }
    const result = new Map<string, DonutSlice[]>();
    for (const [area, catMap] of map) {
      const slices: DonutSlice[] = drillCategory
        ? [...catMap.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5)
            .map(([key, value], i) => ({ key, value, color: SUB_COLORS[i % SUB_COLORS.length] }))
        : [...catMap.entries()].map(([key, value]) => ({ key, value, color: CAT_COLORS[key] ?? '#94a3b8' }));
      result.set(area, slices);
    }
    return result;
  }, [chartType, stores, storeSettings.categories, areaDefs, drillCategory]);

  const ftByArea = useMemo(() => {
    if (chartType !== 'sparkline' || !foottrafficData) return new Map<string, number[]>();
    const { dayweek, agrde } = foottrafficSettings;
    const tmzons = foottrafficData.meta.tmzon_list;
    const map = new Map<string, number[]>();
    for (const link of foottrafficData.links) {
      const area = findArea(link.centroid[0], link.centroid[1], areaDefs);
      if (area === '기타') continue;
      const slice = link.data?.[dayweek]?.[agrde];
      if (!slice) continue;
      if (!map.has(area)) map.set(area, new Array(tmzons.length).fill(0));
      const arr = map.get(area)!;
      tmzons.forEach((tz, i) => { arr[i] += slice[tz]?.acost ?? 0; });
    }
    return map;
  }, [chartType, foottrafficData, foottrafficSettings, areaDefs]);

  const busByArea = useMemo(() => {
    if (chartType !== 'bus') return new Map<string, { ride: number; alight: number }>();
    const map = new Map<string, { ride: number; alight: number }>();
    for (const stop of busStopsFull) {
      const area = findArea(stop.lng, stop.lat, areaDefs);
      if (area === '기타') continue;
      const cur = map.get(area) ?? { ride: 0, alight: 0 };
      cur.ride += stop.total_ride;
      cur.alight += stop.total_alight;
      map.set(area, cur);
    }
    return map;
  }, [chartType, busStopsFull, areaDefs]);

  if (chartType === 'none') return null;

  const containerW = window.innerWidth;
  const containerH = window.innerHeight;
  const chartSize = Math.max(36, Math.min(60, viewState.zoom * 3));

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5, overflow: 'hidden' }}>
      {areas.map(area => {
        const [x, y] = projectLngLat(area.position[0], area.position[1], viewState, containerW, containerH);
        if (x < -100 || y < -100 || x > containerW + 100 || y > containerH + 100) return null;

        let content: React.ReactNode = null;
        if (chartType === 'donut') {
          const slices = storeByArea.get(area.name);
          if (!slices || slices.length === 0) return null;
          content = <MiniDonut slices={slices} size={Math.max(chartSize, 44)} />;
        } else if (chartType === 'sparkline') {
          const vals = ftByArea.get(area.name);
          if (!vals) return null;
          content = <MiniSparkline values={vals} color="#f59e0b" size={chartSize} />;
        } else if (chartType === 'bus') {
          const d = busByArea.get(area.name);
          if (!d) return null;
          content = <MiniStackBar ride={d.ride} alight={d.alight} width={chartSize} />;
        }

        return (
          <div key={area.name} style={{
            position: 'absolute',
            left: x - chartSize / 2,
            top: y - chartSize / 2,
            background: 'rgba(15, 23, 42, 0.8)',
            borderRadius: 6,
            padding: 3,
            border: '1px solid rgba(148, 163, 184, 0.2)',
          }}>
            {content}
          </div>
        );
      })}
    </div>
  );
}
