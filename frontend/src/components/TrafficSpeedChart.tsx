import { useRef, useEffect, useState, useMemo } from 'react';
import * as d3 from 'd3';
import type { TrafficSegment, TrafficPatternResponse } from '../api/client';
import type { TrafficMode } from './Sidebar';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

interface Props {
  segments: TrafficSegment[];
  currentHour: number;
  trafficMode?: TrafficMode;
  realtimeAvgSpeed?: number | null;
  patternData?: TrafficPatternResponse | null;
}

const ROAD_COLORS = [
  '#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316',
];

const TOP_N = 6;
const AVG_COLOR = '#10b981';
const WEEKDAY_COLOR = '#3b82f6';
const WEEKEND_COLOR = '#f97316';
const REALTIME_COLOR = '#ef4444';

const DAY_BUTTONS: { key: string; label: string; color?: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'weekday', label: '평일', color: WEEKDAY_COLOR },
  { key: 'weekend', label: '주말', color: WEEKEND_COLOR },
  { key: '月', label: '' },
  { key: '월', label: '월' },
  { key: '화', label: '화' },
  { key: '수', label: '수' },
  { key: '목', label: '목' },
  { key: '금', label: '금' },
  { key: '토', label: '토', color: WEEKEND_COLOR },
  { key: '일', label: '일', color: '#ef4444' },
];

function isWeekend(): boolean {
  const day = new Date().getDay();
  return day === 0 || day === 6;
}

export default function TrafficSpeedChart({ segments, currentHour, trafficMode = 'pattern', realtimeAvgSpeed, patternData }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(ref);
  const [highlighted, setHighlighted] = useState<string | null>(null);
  const [dayKey, setDayKey] = useState('all');

  const hasPattern = !!patternData?.overall;
  const usePattern = trafficMode === 'pattern' && hasPattern;
  const showRealtimeLines = trafficMode === 'realtime' && hasPattern;

  // Pattern-based road groups (from TOPIS historical data)
  const patternRoadGroups = useMemo(() => {
    if (!patternData?.roads) return [];
    return Object.entries(patternData.roads)
      .map(([name, speeds]) => ({
        name,
        speeds: speeds[dayKey] ?? speeds['all'] ?? Array(24).fill(0) as number[],
      }))
      .sort((a, b) => {
        const aMax = d3.max(a.speeds) ?? 0;
        const bMax = d3.max(b.speeds) ?? 0;
        return bMax - aMax;
      })
      .slice(0, TOP_N);
  }, [patternData, dayKey]);

  const patternAvgSpeeds = useMemo(() => {
    if (!patternData?.overall) return Array(24).fill(0) as number[];
    return patternData.overall[dayKey] ?? patternData.overall['all'] ?? Array(24).fill(0);
  }, [patternData, dayKey]);

  // Segment-based road groups (fallback from silver data)
  const segmentRoadGroups = useMemo(() => {
    const grouped = new Map<string, TrafficSegment[]>();
    for (const s of segments) {
      if (!s.road_name) continue;
      const list = grouped.get(s.road_name) ?? [];
      list.push(s);
      grouped.set(s.road_name, list);
    }
    return Array.from(grouped.entries())
      .map(([name, segs]) => ({
        name,
        speeds: Array.from({ length: 24 }, (_, h) => {
          const vals = segs.map(s => s.speeds[h]).filter(v => v > 0);
          return vals.length > 0 ? d3.mean(vals)! : 0;
        }),
      }))
      .sort((a, b) => (d3.max(b.speeds) ?? 0) - (d3.max(a.speeds) ?? 0))
      .slice(0, TOP_N);
  }, [segments]);

  const segmentAvgSpeeds = useMemo(
    () => Array.from({ length: 24 }, (_, h) => {
      const vals = segments.map(s => s.speeds[h]).filter(v => v > 0);
      return vals.length > 0 ? d3.mean(vals)! : 0;
    }),
    [segments],
  );

  const roadGroups = usePattern ? patternRoadGroups : segmentRoadGroups;
  const avgSpeeds = usePattern ? patternAvgSpeeds : segmentAvgSpeeds;

  useEffect(() => {
    const el = ref.current;
    if (!el || (segments.length === 0 && !hasPattern)) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 240;
    const margin = { top: 12, right: 16, bottom: 32, left: 42 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).select('svg').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const allMaxes = [d3.max(avgSpeeds) ?? 60, ...roadGroups.map(r => d3.max(r.speeds) ?? 0)];
    if (showRealtimeLines && patternData?.overall) {
      allMaxes.push(d3.max(patternData.overall.weekday) ?? 0);
      allMaxes.push(d3.max(patternData.overall.weekend) ?? 0);
    }
    if (realtimeAvgSpeed) allMaxes.push(realtimeAvgSpeed);
    const yMax = d3.max(allMaxes) ?? 60;

    const x = d3.scaleLinear().domain([0, 23]).range([0, iw]);
    const y = d3.scaleLinear().domain([0, yMax]).nice().range([ih, 0]);

    g.append('g')
      .attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(8).tickFormat(h => `${h}시`))
      .selectAll('text')
      .style('font-size', '9px')
      .style('fill', '#64748b');

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(v => `${v}`))
      .selectAll('text')
      .style('font-size', '9px')
      .style('fill', '#64748b');

    g.selectAll('.domain').remove();

    const line = d3
      .line<number>()
      .x((_, i) => x(i))
      .y(d => y(d))
      .curve(d3.curveMonotoneX);

    const area = d3
      .area<number>()
      .x((_, i) => x(i))
      .y0(ih)
      .y1(d => y(d))
      .curve(d3.curveMonotoneX);

    if (showRealtimeLines && patternData?.overall) {
      // ── Realtime mode: weekday/weekend pattern ──
      const todayPattern = isWeekend() ? patternData.overall.weekend : patternData.overall.weekday;
      g.append('path')
        .datum(todayPattern)
        .attr('fill', isWeekend() ? 'rgba(249, 115, 22, 0.08)' : 'rgba(59, 130, 246, 0.08)')
        .attr('d', area);

      g.append('path')
        .datum(patternData.overall.weekday)
        .attr('fill', 'none')
        .attr('stroke', WEEKDAY_COLOR)
        .attr('stroke-width', 1.8)
        .attr('stroke-dasharray', '6,3')
        .attr('stroke-opacity', 0.7)
        .attr('d', line);

      g.append('path')
        .datum(patternData.overall.weekend)
        .attr('fill', 'none')
        .attr('stroke', WEEKEND_COLOR)
        .attr('stroke-width', 1.8)
        .attr('stroke-dasharray', '6,3')
        .attr('stroke-opacity', 0.7)
        .attr('d', line);

    } else {
      // ── Pattern mode ──
      g.append('path')
        .datum(avgSpeeds)
        .attr('fill', highlighted ? 'rgba(16, 185, 129, 0.05)' : 'rgba(16, 185, 129, 0.12)')
        .attr('d', area);

      g.append('path')
        .datum(avgSpeeds)
        .attr('fill', 'none')
        .attr('stroke', AVG_COLOR)
        .attr('stroke-width', highlighted ? 1.2 : 2)
        .attr('stroke-opacity', highlighted ? 0.35 : 1)
        .attr('d', line);

      roadGroups.forEach((road, idx) => {
        const color = ROAD_COLORS[idx % ROAD_COLORS.length];
        const isActive = highlighted === road.name;
        const isDimmed = highlighted !== null && !isActive;

        g.append('path')
          .datum(road.speeds)
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', isActive ? 2.5 : 1.2)
          .attr('stroke-opacity', isDimmed ? 0.15 : isActive ? 1 : 0.6)
          .attr('stroke-dasharray', isActive ? 'none' : '4,2')
          .attr('d', line);
      });
    }

    // ── Current-hour marker ──
    g.append('line')
      .attr('x1', x(currentHour)).attr('x2', x(currentHour))
      .attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#f59e0b')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,3');

    if (!showRealtimeLines) {
      g.append('circle')
        .attr('cx', x(currentHour))
        .attr('cy', y(avgSpeeds[currentHour] ?? 0))
        .attr('r', 4)
        .attr('fill', '#f59e0b');

      g.append('text')
        .attr('x', x(currentHour) + 6)
        .attr('y', y(avgSpeeds[currentHour] ?? 0) - 6)
        .text(`${(avgSpeeds[currentHour] ?? 0).toFixed(1)} km/h`)
        .style('font-size', '10px')
        .style('fill', '#f59e0b')
        .style('font-family', "'JetBrains Mono', monospace");
    }

    // ── Realtime star marker ──
    if (trafficMode === 'realtime' && realtimeAvgSpeed != null && realtimeAvgSpeed > 0) {
      const nowH = new Date().getHours();
      const rtX = x(nowH);
      const rtY = y(Math.min(realtimeAvgSpeed, yMax));

      const starPath = d3.symbol().type(d3.symbolStar).size(150);
      g.append('path')
        .attr('d', starPath()!)
        .attr('transform', `translate(${rtX},${rtY})`)
        .attr('fill', REALTIME_COLOR)
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5);

      const todayPatternSpeed = showRealtimeLines && patternData?.overall
        ? (isWeekend() ? patternData.overall.weekend[nowH] : patternData.overall.weekday[nowH])
        : (avgSpeeds[nowH] ?? 0);
      const diff = realtimeAvgSpeed - todayPatternSpeed;
      const diffSign = diff >= 0 ? '+' : '';
      const dayLabel = showRealtimeLines ? (isWeekend() ? '주말패턴' : '평일패턴') : '패턴';

      const labelY = rtY - 14;
      const labelX = rtX > iw * 0.7 ? rtX - 8 : rtX + 8;
      const anchor = rtX > iw * 0.7 ? 'end' : 'start';

      g.append('text')
        .attr('x', labelX).attr('y', labelY)
        .attr('text-anchor', anchor)
        .style('font-size', '10px').style('font-weight', '700')
        .style('fill', REALTIME_COLOR)
        .style('font-family', "'JetBrains Mono', monospace")
        .text(`★ 실시간 ${realtimeAvgSpeed.toFixed(1)} km/h`);

      g.append('text')
        .attr('x', labelX).attr('y', labelY + 13)
        .attr('text-anchor', anchor)
        .style('font-size', '9px')
        .style('fill', diff >= 0 ? '#10b981' : '#ef4444')
        .style('font-family', "'JetBrains Mono', monospace")
        .text(`(${dayLabel}대비 ${diffSign}${diff.toFixed(1)})`);

      if (showRealtimeLines && patternData?.overall) {
        g.append('circle')
          .attr('cx', rtX).attr('cy', y(patternData.overall.weekday[nowH]))
          .attr('r', 3)
          .attr('fill', WEEKDAY_COLOR).attr('stroke', '#fff').attr('stroke-width', 1);
        g.append('circle')
          .attr('cx', rtX).attr('cy', y(patternData.overall.weekend[nowH]))
          .attr('r', 3)
          .attr('fill', WEEKEND_COLOR).attr('stroke', '#fff').attr('stroke-width', 1);
      }
    }

    // ── Tooltip ──
    const tooltipGroup = g.append('g').attr('class', 'tooltip-group').style('display', 'none');
    const guideLine = tooltipGroup.append('line')
      .attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '3,2');

    const tooltipDots: d3.Selection<SVGCircleElement, unknown, null, undefined>[] = [];

    if (showRealtimeLines) {
      tooltipDots.push(tooltipGroup.append('circle').attr('r', 3).attr('fill', WEEKDAY_COLOR).attr('stroke', '#1e293b').attr('stroke-width', 1));
      tooltipDots.push(tooltipGroup.append('circle').attr('r', 3).attr('fill', WEEKEND_COLOR).attr('stroke', '#1e293b').attr('stroke-width', 1));
    } else {
      tooltipDots.push(tooltipGroup.append('circle').attr('r', 3).attr('fill', AVG_COLOR).attr('stroke', '#1e293b').attr('stroke-width', 1));
      roadGroups.forEach((_, idx) => {
        tooltipDots.push(tooltipGroup.append('circle').attr('r', 2.5).attr('fill', ROAD_COLORS[idx % ROAD_COLORS.length]).attr('stroke', '#1e293b').attr('stroke-width', 0.8));
      });
    }

    const tooltip = d3.select(el).append('div')
      .style('position', 'absolute').style('pointer-events', 'none').style('display', 'none')
      .style('background', 'rgba(15, 23, 42, 0.92)')
      .style('border', '1px solid rgba(148,163,184,0.25)')
      .style('border-radius', '6px').style('padding', '8px 10px')
      .style('font-size', '11px').style('line-height', '1.6')
      .style('color', '#e2e8f0')
      .style('font-family', "'JetBrains Mono', monospace")
      .style('z-index', '10').style('white-space', 'nowrap');

    const overlay = g.append('rect').attr('width', iw).attr('height', ih).attr('fill', 'transparent').style('cursor', 'crosshair');

    const visibleRoads = roadGroups.filter(road => highlighted === null || highlighted === road.name);

    overlay
      .on('mousemove', (event: MouseEvent) => {
        const [mx] = d3.pointer(event);
        const h = Math.max(0, Math.min(23, Math.round(x.invert(mx))));

        tooltipGroup.style('display', null);
        tooltip.style('display', null);
        guideLine.attr('x1', x(h)).attr('x2', x(h));

        let html = `<div style="margin-bottom:4px;font-weight:600;color:#f8fafc">${h}시</div>`;

        if (showRealtimeLines && patternData?.overall) {
          const wdSpeed = patternData.overall.weekday[h];
          const weSpeed = patternData.overall.weekend[h];
          tooltipDots[0].attr('cx', x(h)).attr('cy', y(wdSpeed));
          tooltipDots[1].attr('cx', x(h)).attr('cy', y(weSpeed));
          html += `<div style="color:${WEEKDAY_COLOR}">평일: ${wdSpeed.toFixed(1)} km/h</div>`;
          html += `<div style="color:${WEEKEND_COLOR}">주말: ${weSpeed.toFixed(1)} km/h</div>`;
          const diff = wdSpeed - weSpeed;
          html += `<div style="color:#94a3b8;font-size:10px">차이: ${diff >= 0 ? '+' : ''}${diff.toFixed(1)}</div>`;
        } else {
          tooltipDots[0].attr('cx', x(h)).attr('cy', y(avgSpeeds[h] ?? 0)).style('display', null);
          roadGroups.forEach((road, idx) => {
            const isDimmed = highlighted !== null && highlighted !== road.name;
            tooltipDots[idx + 1]?.attr('cx', x(h)).attr('cy', y(road.speeds[h] ?? 0)).style('display', isDimmed ? 'none' : null);
          });
          const rows: { name: string; speed: number; color: string }[] = [
            { name: '성수 평균', speed: avgSpeeds[h] ?? 0, color: AVG_COLOR },
          ];
          for (const road of (highlighted ? visibleRoads : roadGroups)) {
            const origIdx = roadGroups.indexOf(road);
            rows.push({ name: road.name, speed: road.speeds[h] ?? 0, color: ROAD_COLORS[origIdx % ROAD_COLORS.length] });
          }
          rows.sort((a, b) => b.speed - a.speed);
          for (const r of rows) {
            html += `<div style="color:${r.color}">${r.name}: ${r.speed.toFixed(1)} km/h</div>`;
          }
        }

        tooltip.html(html);
        const tw = (tooltip.node() as HTMLDivElement).offsetWidth;
        const tipX = x(h) + margin.left;
        const flipped = tipX + tw + 14 > width;
        tooltip
          .style('left', flipped ? `${tipX - tw - 10}px` : `${tipX + 14}px`)
          .style('top', `${margin.top + 4}px`);
      })
      .on('mouseleave', () => {
        tooltipGroup.style('display', 'none');
        tooltip.style('display', 'none');
      });

    return () => { tooltip.remove(); };
  }, [segments, currentHour, roadGroups, avgSpeeds, highlighted, resizeKey, trafficMode,
      realtimeAvgSpeed, patternData, showRealtimeLines, usePattern, hasPattern, dayKey]);

  return (
    <div style={{ position: 'relative' }}>
      {/* Day-of-week buttons (pattern mode with TOPIS data) */}
      {usePattern && (
        <div className="tsc-day-bar">
          {DAY_BUTTONS.map(btn => {
            if (btn.key === '月') return <span key="sep" className="tsc-day-sep" />;
            const active = dayKey === btn.key;
            return (
              <button
                key={btn.key}
                className={`tsc-day-btn${active ? ' active' : ''}`}
                style={active && btn.color ? { borderColor: btn.color, color: btn.color } : undefined}
                onClick={() => setDayKey(btn.key)}
              >
                {btn.label}
              </button>
            );
          })}
        </div>
      )}

      <div ref={ref} className="chart-container" />

      {/* Legend */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px', padding: '4px 8px 0', fontSize: 10 }}>
        {showRealtimeLines ? (
          <>
            <span style={{ color: WEEKDAY_COLOR, fontWeight: 600 }}>┅ 평일 패턴</span>
            <span style={{ color: WEEKEND_COLOR, fontWeight: 600 }}>┅ 주말 패턴</span>
            {realtimeAvgSpeed != null && <span style={{ color: REALTIME_COLOR, fontWeight: 600 }}>★ 실시간</span>}
            {patternData?.meta?.months && (
              <span style={{ color: '#64748b', fontSize: 9 }}>({patternData.meta.months.length}개월 평균)</span>
            )}
          </>
        ) : (
          <>
            <span
              style={{ cursor: 'pointer', opacity: highlighted === null ? 1 : 0.5, fontWeight: highlighted === null ? 600 : 400, color: AVG_COLOR }}
              onClick={() => setHighlighted(null)}
            >
              ● 성수 평균
            </span>
            {roadGroups.map((road, idx) => {
              const color = ROAD_COLORS[idx % ROAD_COLORS.length];
              const isActive = highlighted === road.name;
              return (
                <span
                  key={road.name}
                  style={{ cursor: 'pointer', opacity: highlighted !== null && !isActive ? 0.4 : 1, fontWeight: isActive ? 600 : 400, color }}
                  onClick={() => setHighlighted(prev => (prev === road.name ? null : road.name))}
                >
                  ● {road.name}
                </span>
              );
            })}
            {usePattern && patternData?.meta?.months && (
              <span style={{ color: '#64748b', fontSize: 9 }}>({patternData.meta.months.length}개월 평균)</span>
            )}
          </>
        )}
      </div>
    </div>
  );
}
