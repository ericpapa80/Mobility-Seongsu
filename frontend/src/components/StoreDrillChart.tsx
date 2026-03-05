import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import type { Store, GeoJSONCollection } from '../api/client';
import type { StoreSettings } from './Sidebar';
import type { AreaDef } from '../lib/geo';
import { extractAreas, findArea, polygonCentroid } from '../lib/geo';
import { fmtWon } from '../lib/format';
import StoreTimeFlowChart from './StoreTimeFlowChart';
import StoreWeekdayChart from './StoreWeekdayChart';
import StoreDemoChart from './StoreDemoChart';
import StoreFamChart from './StoreFamChart';
import StorePecoChart from './StorePecoChart';
import StoreWdweChart from './StoreWdweChart';
import StoreRevfreqChart from './StoreRevfreqChart';
import StoreTrendChart from './StoreTrendChart';
import './StoreDrillChart.css';
import './ChartCommon.css';

function useContainerWidth(ref: React.RefObject<HTMLDivElement | null>) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const cr = entries[0]?.contentRect;
      if (cr) setW(Math.round(cr.width));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

/* ── Types ── */

export type DrillLevel = 'all' | 'category' | 'area-grid' | 'area-detail';

export interface DrillState {
  level: DrillLevel;
  category?: string;
  area?: string;
}

interface Props {
  stores: Store[];
  settings: StoreSettings;
  currentHour: number;
  commercialAreaGeoJson: GeoJSONCollection | null;
  onDrillStateChange?: (state: DrillState) => void;
  onFilteredChange?: (stores: Store[], settings: StoreSettings, drill: DrillState) => void;
  expanded?: boolean;
}

interface DonutEntry { key: string; value: number; color: string }


/* ── Color maps ── */

const CAT_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};

const SUB_COLORS = [
  '#f59e0b', '#10b981', '#a78bfa', '#22d3ee', '#f87171',
  '#84cc16', '#fb923c', '#60a5fa', '#e879f9', '#94a3b8',
];

/* ── Breadcrumb ── */

function Breadcrumb({ drill, onNavigate }: {
  drill: DrillState;
  onNavigate: (s: DrillState) => void;
}) {
  type Crumb = { label: string; state: DrillState };

  const crumbs: Crumb[] = [{ label: '성수동 전체', state: { level: 'all' } }];

  if (drill.level === 'category' && drill.category) {
    crumbs.push({ label: drill.category, state: { level: 'category', category: drill.category } });
  } else if (drill.level === 'area-grid') {
    if (drill.category) {
      crumbs.push({ label: drill.category, state: { level: 'category', category: drill.category } });
    }
    crumbs.push({ label: '상권별', state: drill });
  } else if (drill.level === 'area-detail') {
    if (drill.category) {
      crumbs.push({ label: drill.category, state: { level: 'category', category: drill.category } });
    }
    crumbs.push({ label: '상권별', state: { level: 'area-grid', category: drill.category } });
    if (drill.area) {
      crumbs.push({ label: drill.area, state: drill });
    }
  }

  if (crumbs.length <= 1) return null;

  return (
    <div className="drill-breadcrumb">
      {crumbs.map((c, i) => (
        <span key={i} className="drill-crumb-item">
          {i > 0 && <span className="drill-sep">›</span>}
          <button
            className={`drill-crumb${i === crumbs.length - 1 ? ' active' : ''}`}
            onClick={() => { if (i < crumbs.length - 1) onNavigate(c.state); }}
            disabled={i === crumbs.length - 1}
          >
            {c.label}
          </button>
        </span>
      ))}
    </div>
  );
}

/* ── Drilldown Donut (D3) ── */

function DrillDonut({ data, onSliceClick, areaBtn, onAreaClick }: {
  data: DonutEntry[];
  onSliceClick?: (key: string) => void;
  areaBtn?: boolean;
  onAreaClick?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const containerWidth = useContainerWidth(ref);

  const onSliceClickRef = useRef(onSliceClick);
  onSliceClickRef.current = onSliceClick;
  const onAreaClickRef = useRef(onAreaClick);
  onAreaClickRef.current = onAreaClick;

  useEffect(() => {
    const el = ref.current;
    if (!el || data.length === 0) return;

    const w = containerWidth || el.getBoundingClientRect().width || 340;
    const donutR = Math.min(w * 0.28, 78);
    const margin = { top: 20, right: 8, bottom: 6, left: 4 };
    const donutH = margin.top + donutR * 2 + margin.bottom;
    const legendEntryH = 17;
    const legendH = margin.top + data.length * legendEntryH + margin.bottom;
    const h = Math.max(donutH, legendH);

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', w).attr('height', h);

    const cx = donutR + margin.left + 6;
    const cy = margin.top + donutR;
    const gDonut = svg.append('g').attr('transform', `translate(${cx},${cy})`);

    const pie = d3.pie<DonutEntry>().value(d => d.value).sort(null);
    const arc = d3.arc<d3.PieArcDatum<DonutEntry>>()
      .innerRadius(donutR * 0.55)
      .outerRadius(donutR);

    const paths = gDonut.selectAll('path')
      .data(pie(data))
      .join('path')
      .attr('d', arc)
      .attr('fill', d => d.data.color)
      .attr('stroke', '#0c0c0c')
      .attr('stroke-width', 1.5)
      .style('cursor', onSliceClickRef.current ? 'pointer' : 'default');

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');

    paths
      .on('mouseenter', function(_e: MouseEvent, d: d3.PieArcDatum<DonutEntry>) {
        d3.select(this).attr('opacity', 0.72);
        const hasAction = !!onSliceClickRef.current;
        tooltip.style('opacity', '1').html(
          `<b>${d.data.key}</b><br/>${fmtWon(d.data.value)}원`
          + (hasAction ? '<br/><span style="opacity:0.5;font-size:9px">▸ 드릴다운</span>' : ''),
        );
      })
      .on('mousemove', (event: MouseEvent) => {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', function() {
        d3.select(this).attr('opacity', 1);
        tooltip.style('opacity', '0');
      })
      .on('click', (_e: MouseEvent, d: d3.PieArcDatum<DonutEntry>) => {
        onSliceClickRef.current?.(d.data.key);
      });

    const fmtVal = fmtWon;

    const total = data.reduce((s, d) => s + d.value, 0);
    const mainFontSize = Math.max(13, Math.round(donutR * 0.22));
    const centerText = gDonut.append('text').attr('text-anchor', 'middle').attr('dy', '0.35em')
      .style('font-weight', '700').style('fill', '#e2e8f0');
    centerText.append('tspan')
      .text(fmtWon(total))
      .style('font-size', `${mainFontSize}px`);
    centerText.append('tspan')
      .text('원')
      .style('font-size', '10px')
      .style('font-weight', '400')
      .style('fill', '#94a3b8')
      .attr('dy', '0')
      .attr('alignment-baseline', 'baseline');

    // Legend — right edge aligned with "상권별" button right edge (w - 4)
    const btnRightEdge = w - 4;
    const legendY = cy - (data.length * legendEntryH) / 2 + 8;
    const minGap = 12;
    const donutRight = cx + donutR;
    const labelGap = 6; // fixed gap between label text and number

    // Render labels offscreen first to measure actual text widths
    const measureG = svg.append('g').style('visibility', 'hidden');
    const truncMax = 8;
    const measured = data.map(d => {
      const label = d.key.length > truncMax ? d.key.slice(0, truncMax) + '…' : d.key;
      const t = measureG.append('text').text(label).style('font-size', '10px');
      const tw = (t.node() as SVGTextElement).getComputedTextLength();
      return { label, tw };
    });
    const maxLabelW = Math.max(...measured.map(m => m.tw));
    measureG.remove();

    // Monospace number column width
    const maxNumLen = Math.max(...data.map(d => fmtWon(d.value).length));
    const numColW = maxNumLen * 7;
    const numRightX = 12 + maxLabelW + labelGap + numColW;

    // Ensure minimum gap from donut; shorten labels if needed
    let legendX = btnRightEdge - numRightX;
    if (legendX < donutRight + minGap) {
      const budget = btnRightEdge - (donutRight + minGap) - 12 - labelGap - numColW;
      // Re-truncate labels to fit within budget
      const retruncated = data.map(d => {
        let lbl = d.key;
        while (lbl.length > 2) {
          const mG = svg.append('g').style('visibility', 'hidden');
          const t = mG.append('text').text(lbl.length <= truncMax ? lbl : lbl.slice(0, truncMax) + '…').style('font-size', '10px');
          const tw = (t.node() as SVGTextElement).getComputedTextLength();
          mG.remove();
          if (tw <= budget) return lbl.length <= truncMax ? lbl : lbl.slice(0, truncMax) + '…';
          lbl = lbl.slice(0, -1);
        }
        return lbl + '…';
      });
      const mG2 = svg.append('g').style('visibility', 'hidden');
      const finalMaxW = Math.max(...retruncated.map(l => {
        const t = mG2.append('text').text(l).style('font-size', '10px');
        return (t.node() as SVGTextElement).getComputedTextLength();
      }));
      mG2.remove();
      const finalNumRightX = 12 + finalMaxW + labelGap + numColW;
      legendX = btnRightEdge - finalNumRightX;
      measured.forEach((m, i) => { m.label = retruncated[i]; m.tw = finalMaxW; });
    }

    const gLeg = svg.append('g').attr('transform', `translate(${legendX},${legendY})`);
    data.forEach((d, i) => {
      const row = gLeg.append('g').attr('transform', `translate(0,${i * legendEntryH})`);
      row.append('rect').attr('width', 8).attr('height', 8).attr('rx', 1.5).attr('fill', d.color);
      const legFont = "'Pretendard', 'Noto Sans KR', sans-serif";
      row.append('text').attr('x', 12).attr('y', 7.5).attr('text-anchor', 'start')
        .text(measured[i].label).style('font-size', '10px').style('fill', '#cbd5e1')
        .style('font-family', legFont);
      row.append('text').attr('x', btnRightEdge - legendX).attr('y', 7.5).attr('text-anchor', 'end')
        .text(fmtWon(d.value))
        .style('font-size', '10px').style('fill', '#94a3b8')
        .style('font-family', legFont)
        .style('font-variant-numeric', 'tabular-nums');
    });

    // "상권별" area button (top-right)
    if (areaBtn && onAreaClickRef.current) {
      const btn = svg.append('g')
        .attr('transform', `translate(${w - 36}, 2)`)
        .style('cursor', 'pointer')
        .on('click', () => onAreaClickRef.current?.());
      btn.append('rect').attr('width', 32).attr('height', 18).attr('rx', 4)
        .attr('fill', 'rgba(6,182,212,0.12)')
        .attr('stroke', 'rgba(6,182,212,0.5)').attr('stroke-width', 1);
      btn.append('text').attr('x', 16).attr('y', 13).attr('text-anchor', 'middle')
        .text('상권별').style('font-size', '8px').style('fill', '#22d3ee').style('font-weight', '700');
    }
  }, [data, areaBtn, containerWidth]);

  const minH = Math.max(184, data.length * 17 + 30);
  return <div ref={ref} className="chart-container" style={{ minHeight: minH }} />;
}

/* ── Mini Donut SVG (for area grid) ── */

function MiniDonutSVG({ data, size }: { data: DonutEntry[]; size: number }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;
  const r = size / 2;
  const ir = r * 0.45;
  let cumAngle = -Math.PI / 2;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: 'block' }}>
      {data.map(d => {
        const sweep = (d.value / total) * 2 * Math.PI;
        const start = cumAngle;
        cumAngle += sweep;
        const end = cumAngle;
        const la = sweep > Math.PI ? 1 : 0;
        const x1 = r + r * Math.cos(start), y1 = r + r * Math.sin(start);
        const x2 = r + r * Math.cos(end), y2 = r + r * Math.sin(end);
        const ix1 = r + ir * Math.cos(start), iy1 = r + ir * Math.sin(start);
        const ix2 = r + ir * Math.cos(end), iy2 = r + ir * Math.sin(end);
        const p = `M${x1},${y1} A${r},${r} 0 ${la},1 ${x2},${y2} L${ix2},${iy2} A${ir},${ir} 0 ${la},0 ${ix1},${iy1} Z`;
        return <path key={d.key} d={p} fill={d.color} opacity={0.85} />;
      })}
    </svg>
  );
}

/* ── Area Map View (폴리곤 경계 + centroid 파이) ── */

function AreaMapView({ areas, geoJson, stores, settings, filterCategory, onAreaClick }: {
  areas: AreaDef[];
  geoJson: GeoJSONCollection;
  stores: Store[];
  settings: StoreSettings;
  filterCategory?: string;
  onAreaClick: (area: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const fmtVal = fmtWon;

  const cellMap = useMemo(() => {
    const filtered = stores.filter(s => {
      if (!settings.categories.includes(s.category_bg)) return false;
      if (filterCategory && s.category_bg !== filterCategory) return false;
      return true;
    });
    const result = new Map<string, { slices: DonutEntry[]; total: number }>();
    for (const a of areas) {
      const aStores = filtered.filter(s => findArea(s.lng, s.lat, areas) === a.name);
      const map = new Map<string, number>();
      for (const s of aStores) {
        const key = filterCategory ? s.category_mi : s.category_bg;
        map.set(key, (map.get(key) ?? 0) + s.peco_total);
      }
      const sorted = [...map.entries()].sort((x, y) => y[1] - x[1]);
      const TOP_N = 5;
      const top = sorted.slice(0, TOP_N);
      const rest = sorted.slice(TOP_N);
      const slices: DonutEntry[] = filterCategory
        ? top.map(([k, v], i) => ({ key: k, value: v, color: SUB_COLORS[i % SUB_COLORS.length] }))
        : top.map(([k, v]) => ({ key: k, value: v, color: CAT_COLORS[k] ?? '#94a3b8' }));
      if (rest.length > 0) {
        slices.push({ key: '기타', value: rest.reduce((s, [, v]) => s + v, 0), color: '#475569' });
      }
      const total = slices.reduce((s, d) => s + d.value, 0);
      if (total > 0) result.set(a.name, { slices, total });
    }
    return result;
  }, [areas, stores, settings.categories, filterCategory]);

  // Compute SVG dimensions from container width
  const [svgW, setSvgW] = useState(340);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 0) setSvgW(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // d3 projection: fit all polygons into [svgW × svgH]
  const svgH = Math.round(svgW * 0.72); // aspect ratio from attached map image

  // Manual centroid nudges (in pixels at 340px base width) to prevent label/pie overlap
  const CENTROID_NUDGE: Record<string, [number, number]> = {
    '새촌': [-0.01, 0.06],   // move west-south (as fraction of svgW/svgH)
  };

  const { projection, pathGen, featureData } = useMemo(() => {
    const proj = d3.geoMercator().fitSize([svgW, svgH], geoJson as Parameters<typeof proj.fitSize>[1]);
    const pg = d3.geoPath(proj);

    const data = geoJson.features.map(f => {
      const name = f.properties['상권명'] as string;
      const ring = (f.geometry.coordinates as number[][][][])[0][0];
      const [clng, clat] = polygonCentroid(ring);
      let [cx, cy] = proj([clng, clat]) ?? [0, 0];
      const nudge = CENTROID_NUDGE[name];
      if (nudge) { cx += nudge[0] * svgW; cy += nudge[1] * svgH; }
      const cell = cellMap.get(name);
      return { name, feature: f, cx, cy, cell };
    });
    return { projection: proj, pathGen: pg, featureData: data };
  // CENTROID_NUDGE is a constant, excluded from deps intentionally
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geoJson, svgW, svgH, cellMap]);

  if (cellMap.size === 0) {
    return <div className="drill-empty">상권 데이터가 없습니다</div>;
  }

  const PIE_SIZE = Math.round(svgW * 0.13); // ~44px at 340px width

  // Collect unique legend entries from all visible cells
  const legendEntries = useMemo(() => {
    const seen = new Map<string, string>();
    for (const cell of cellMap.values()) {
      for (const s of cell.slices) {
        if (!seen.has(s.key)) seen.set(s.key, s.color);
      }
    }
    return [...seen.entries()].map(([key, color]) => ({ key, color }));
  }, [cellMap]);

  // Pre-calculate legend row count for SVG height
  const legendRowH = 13;
  const legendPadL = 6;   // left padding
  const legendPadR = 54;  // right padding — controls max row width
  const legendItemGap = 4;
  const legendBoxW = 6;
  const legendBoxGap = 3;
  const legendCharW = 7.5;
  const legendRows = useMemo(() => {
    const maxW = svgW - legendPadL - legendPadR;
    const rows: { label: string; color: string; w: number }[][] = [[]];
    let rowW = 0;
    for (const { key, color } of legendEntries) {
      const label = key;
      const w = legendBoxW + legendBoxGap + label.length * legendCharW;
      if (rows[rows.length - 1].length > 0 && rowW + legendItemGap + w > maxW) {
        rows.push([]);
        rowW = 0;
      }
      if (rows[rows.length - 1].length > 0) rowW += legendItemGap;
      rows[rows.length - 1].push({ label, color, w });
      rowW += w;
    }
    return rows;
  }, [legendEntries, svgW]);
  const legendTotalH = legendEntries.length > 0 ? legendRows.length * legendRowH + 24 : 0;
  const totalSvgH = svgH + legendTotalH;

  return (
    <div ref={ref} className="drill-area-map">
      <svg width={svgW} height={totalSvgH} style={{ display: 'block' }}>
        {/* Polygon boundaries */}
        {featureData.map(({ name, feature }) => (
          <path
            key={`poly-${name}`}
            d={pathGen(feature as Parameters<typeof pathGen>[0]) ?? ''}
            fill={hovered === name ? 'rgba(6,182,212,0.18)' : 'rgba(6,182,212,0.07)'}
            stroke={hovered === name ? 'rgba(6,182,212,0.9)' : 'rgba(6,182,212,0.4)'}
            strokeWidth={hovered === name ? 1.5 : 0.8}
            style={{ cursor: cellMap.has(name) ? 'pointer' : 'default', transition: 'fill 0.15s, stroke 0.15s' }}
            onMouseEnter={() => setHovered(name)}
            onMouseLeave={() => setHovered(null)}
            onClick={() => cellMap.has(name) && onAreaClick(name)}
          />
        ))}

        {/* Centroid pie charts + labels */}
        {featureData.map(({ name, cx, cy, cell }) => {
          if (!cell) return null;
          const r = PIE_SIZE / 2;
          return (
            <g
              key={`chart-${name}`}
              transform={`translate(${cx - r},${cy - r})`}
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHovered(name)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onAreaClick(name)}
            >
              {/* Donut slices */}
              {(() => {
                const total = cell.slices.reduce((s, d) => s + d.value, 0);
                const ir = r * 0.42;
                let cum = -Math.PI / 2;
                return cell.slices.map(d => {
                  const sweep = (d.value / total) * 2 * Math.PI;
                  const start = cum;
                  cum += sweep;
                  const end = cum;
                  const la = sweep > Math.PI ? 1 : 0;
                  const x1 = r + r * Math.cos(start), y1 = r + r * Math.sin(start);
                  const x2 = r + r * Math.cos(end), y2 = r + r * Math.sin(end);
                  const ix1 = r + ir * Math.cos(start), iy1 = r + ir * Math.sin(start);
                  const ix2 = r + ir * Math.cos(end), iy2 = r + ir * Math.sin(end);
                  const p = `M${x1},${y1} A${r},${r} 0 ${la},1 ${x2},${y2} L${ix2},${iy2} A${ir},${ir} 0 ${la},0 ${ix1},${iy1} Z`;
                  return (
                    <path key={d.key} d={p} fill={d.color}
                      opacity={hovered === name ? 1 : 0.85}
                      stroke="#0c0c0c" strokeWidth={0.6} />
                  );
                });
              })()}
              {/* Sales amount in donut center */}
              {(() => {
                const total = cell.slices.reduce((s, d) => s + d.value, 0);
                const fs = Math.max(8, Math.round(PIE_SIZE * 0.20));
                const textProps = {
                  x: r, y: r + fs * 0.4,
                  textAnchor: 'middle' as const,
                  fontSize: fs,
                  fontWeight: 400,
                  fontFamily: "'Pretendard', 'Noto Sans KR', sans-serif",
                };
                return (
                  <>
                    {/* White outline buffer */}
                    <text {...textProps} fill="none" stroke="rgba(255,255,255,0.70)" strokeWidth={3} strokeLinejoin="round" paintOrder="stroke">
                      {fmtVal(total)}
                    </text>
                    <text {...textProps} fill="#1e293b">
                      {fmtVal(total)}
                    </text>
                  </>
                );
              })()}
              {/* Area name label */}
              <text
                x={r} y={PIE_SIZE + 10}
                textAnchor="middle"
                fill={hovered === name ? '#e2e8f0' : '#94a3b8'}
                fontSize={Math.max(8, Math.round(PIE_SIZE * 0.22))}
                fontWeight={hovered === name ? 700 : 400}
                style={{ transition: 'fill 0.15s' }}
              >
                {name}
              </text>
            </g>
          );
        })}

        {/* Legend — below map area, auto-wrap */}
        {legendEntries.length > 0 && (() => {
          const ly = svgH + 20; // start below the map area with gap
          return (
            <g>
              {legendRows.map((row, ri) => {
                let x = legendPadL;
                return row.map((item) => {
                  const tx = x;
                  x += item.w + legendItemGap;
                  return (
                    <g key={item.label} transform={`translate(${tx}, ${ly + ri * legendRowH})`}>
                      <rect width={legendBoxW} height={7} rx={1.5} fill={item.color} y={0} />
                      <text x={legendBoxW + legendBoxGap} y={7.5} fontSize={8.5} fill="#cbd5e1"
                        fontFamily="'Pretendard', 'Noto Sans KR', sans-serif">
                        {item.label}
                      </text>
                    </g>
                  );
                });
              })}
            </g>
          );
        })()}
      </svg>
    </div>
  );
}

/* ── Auxiliary Tabs ── */

type AuxTab = 'time' | 'weekday' | 'demo' | 'fam' | 'peco' | 'wdwe' | 'revfreq' | 'trend';

const AUX_TABS: { key: AuxTab; label: string }[] = [
  { key: 'time', label: '시간대' },
  { key: 'weekday', label: '요일' },
  { key: 'demo', label: '성별연령' },
  { key: 'fam', label: '세대별' },
  { key: 'peco', label: '소비자' },
  { key: 'wdwe', label: '평일/공휴일' },
  { key: 'revfreq', label: '재방문' },
  { key: 'trend', label: '트렌드' },
];

function AuxSection({ stores, settings, currentHour, expanded }: {
  stores: Store[];
  settings: StoreSettings;
  currentHour: number;
  expanded?: boolean;
}) {
  const [tab, setTab] = useState<AuxTab>('time');

  if (expanded) {
    return (
      <div className="drill-aux">
        <div className="drill-sub-title" style={{ marginTop: 0 }}>시간별 매출</div>
        <StoreTimeFlowChart stores={stores} settings={settings} currentHour={currentHour} />
      </div>
    );
  }

  return (
    <div className="drill-aux">
      <div className="chart-mode-btns drill-aux-tabs" style={{ marginBottom: 8 }}>
        {AUX_TABS.map(t => (
          <button key={t.key}
            className={`mode-btn${tab === t.key ? ' active' : ''}`}
            onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'time' && <StoreTimeFlowChart stores={stores} settings={settings} currentHour={currentHour} />}
      {tab === 'weekday' && <StoreWeekdayChart stores={stores} settings={settings} />}
      {tab === 'demo' && <StoreDemoChart stores={stores} settings={settings} />}
      {tab === 'fam' && <StoreFamChart stores={stores} settings={settings} />}
      {tab === 'peco' && <StorePecoChart stores={stores} settings={settings} />}
      {tab === 'wdwe' && <StoreWdweChart stores={stores} settings={settings} />}
      {tab === 'revfreq' && <StoreRevfreqChart stores={stores} settings={settings} />}
      {tab === 'trend' && <StoreTrendChart stores={stores} settings={settings} />}
    </div>
  );
}

/* ── Main Component ── */

export default function StoreDrillChart({
  stores, settings, currentHour, commercialAreaGeoJson, onDrillStateChange, onFilteredChange, expanded,
}: Props) {
  const [drill, setDrill] = useState<DrillState>({ level: 'all' });

  const areas = useMemo(() =>
    commercialAreaGeoJson ? extractAreas(commercialAreaGeoJson) : [],
  [commercialAreaGeoJson]);

  const navigate = useCallback((state: DrillState) => {
    setDrill(state);
    onDrillStateChange?.(state);
  }, [onDrillStateChange]);

  // Auto-navigate back if area data disappears (layer turned off)
  useEffect(() => {
    if ((drill.level === 'area-grid' || drill.level === 'area-detail') && areas.length === 0) {
      navigate({ level: drill.category ? 'category' : 'all', category: drill.category });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [areas.length]);

  // Filtered stores for aux charts based on current drill scope
  const filteredForAux = useMemo(() => {
    let s = stores.filter(st => settings.categories.includes(st.category_bg));
    if (drill.category) s = s.filter(st => st.category_bg === drill.category);
    if (drill.area && areas.length > 0) {
      s = s.filter(st => findArea(st.lng, st.lat, areas) === drill.area);
    }
    return s;
  }, [stores, settings.categories, drill, areas]);

  const auxSettings = useMemo((): StoreSettings => {
    if (drill.category) return { ...settings, categories: [drill.category] };
    return settings;
  }, [settings, drill.category]);

  useEffect(() => {
    onFilteredChange?.(filteredForAux, auxSettings, drill);
  }, [filteredForAux, auxSettings, drill, onFilteredChange]);

  // Level 0: category_bg breakdown
  const allData = useMemo((): DonutEntry[] => {
    const filtered = stores.filter(s => settings.categories.includes(s.category_bg));
    const map = new Map<string, number>();
    for (const s of filtered) map.set(s.category_bg, (map.get(s.category_bg) ?? 0) + s.peco_total);
    return [...map.entries()].sort((a, b) => b[1] - a[1])
      .map(([key, value]) => ({ key, value, color: CAT_COLORS[key] ?? '#94a3b8' }));
  }, [stores, settings.categories]);

  // Level 1a: category_mi breakdown for selected category (top 8 + 기타)
  const categoryData = useMemo((): DonutEntry[] => {
    if (!drill.category) return [];
    const filtered = stores.filter(s => s.category_bg === drill.category);
    const map = new Map<string, number>();
    for (const s of filtered) map.set(s.category_mi, (map.get(s.category_mi) ?? 0) + s.peco_total);
    const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]);
    const TOP_N = 8;
    const top = sorted.slice(0, TOP_N).map(([key, value], i) => ({
      key, value, color: SUB_COLORS[i % SUB_COLORS.length],
    }));
    const rest = sorted.slice(TOP_N);
    if (rest.length > 0) {
      top.push({ key: '기타', value: rest.reduce((s, [, v]) => s + v, 0), color: '#475569' });
    }
    return top;
  }, [stores, drill.category]);

  // Level 2 (area-detail): category_bg or category_mi breakdown for selected area
  const areaDetailData = useMemo((): DonutEntry[] => {
    if (!drill.area || areas.length === 0) return [];
    const filtered = stores.filter(s => {
      if (!settings.categories.includes(s.category_bg)) return false;
      if (drill.category && s.category_bg !== drill.category) return false;
      return findArea(s.lng, s.lat, areas) === drill.area;
    });
    const useMi = !!drill.category;
    const map = new Map<string, number>();
    for (const s of filtered) {
      const k = useMi ? s.category_mi : s.category_bg;
      map.set(k, (map.get(k) ?? 0) + s.peco_total);
    }
    const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]);
    if (useMi) {
      const TOP_N = 8;
      const top = sorted.slice(0, TOP_N).map(([key, value], i) => ({
        key, value, color: SUB_COLORS[i % SUB_COLORS.length],
      }));
      const rest = sorted.slice(TOP_N);
      if (rest.length > 0) {
        top.push({ key: '기타', value: rest.reduce((s, [, v]) => s + v, 0), color: '#475569' });
      }
      return top;
    }
    return sorted.map(([key, value]) => ({ key, value, color: CAT_COLORS[key] ?? '#94a3b8' }));
  }, [stores, settings.categories, drill, areas]);

  const hasAreas = areas.length > 0;

  return (
    <div className="drill-container">
      <div className="drill-top">
        <Breadcrumb drill={drill} onNavigate={navigate} />

      {expanded && drill.level !== 'area-grid' && (
        <div className="drill-sub-title" style={{ marginTop: 0 }}>상가매출 종합</div>
      )}

        {drill.level === 'all' && (
          <DrillDonut
            data={allData}
            onSliceClick={cat => navigate({ level: 'category', category: cat })}
            areaBtn={hasAreas}
            onAreaClick={() => navigate({ level: 'area-grid' })}
          />
        )}

        {drill.level === 'category' && (
          <DrillDonut
            data={categoryData}
            areaBtn={hasAreas}
            onAreaClick={() => navigate({ level: 'area-grid', category: drill.category })}
          />
        )}

        {drill.level === 'area-grid' && commercialAreaGeoJson && (
          <AreaMapView
            areas={areas}
            geoJson={commercialAreaGeoJson}
            stores={stores}
            settings={settings}
            filterCategory={drill.category}
            onAreaClick={area => navigate({ level: 'area-detail', category: drill.category, area })}
          />
        )}

        {drill.level === 'area-detail' && (
          <DrillDonut
            data={areaDetailData}
            onSliceClick={!drill.category
              ? cat => navigate({ level: 'area-detail', category: cat, area: drill.area })
              : undefined}
          />
        )}
      </div>

      {drill.level !== 'area-grid' && (
        <AuxSection stores={filteredForAux} settings={auxSettings} currentHour={currentHour} expanded={expanded} />
      )}
    </div>
  );
}
