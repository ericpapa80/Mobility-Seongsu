import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { SubwayStationHourly } from '../api/client';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

interface Props {
  stations: SubwayStationHourly[];
  currentHour: number;
}

const EXIT_COLORS = [
  '#10b981', '#3b82f6', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
];

export default function SubwayExitChart({ stations, currentHour }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(ref);
  const [selectedStation, setSelectedStation] = useState(0);

  const station = stations[selectedStation];

  useEffect(() => {
    const el = ref.current;
    if (!el || !station) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 200;
    const margin = { top: 12, right: 72, bottom: 28, left: 44 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('svg,.chart-tip').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const exitEntries = Object.entries(station.exit_traffic.by_exit)
      .sort(([a], [b]) => Number(a) - Number(b));

    if (exitEntries.length === 0) {
      g.append('text').attr('x', iw / 2).attr('y', ih / 2)
        .attr('text-anchor', 'middle').attr('fill', 'var(--text-muted)')
        .attr('font-size', 12).text('출구 데이터 없음');
      return;
    }

    const hours = d3.range(24);
    const stackData = hours.map(h => {
      const obj: Record<string, number> = { hour: h };
      for (const [exitNo, hourly] of exitEntries) {
        obj[`exit_${exitNo}`] = hourly[h] ?? 0;
      }
      return obj;
    });

    const keys = exitEntries.map(([no]) => `exit_${no}`);
    const stack = d3.stack<Record<string, number>>().keys(keys).order(d3.stackOrderNone).offset(d3.stackOffsetNone);
    const series = stack(stackData);

    const x = d3.scaleLinear().domain([0, 23]).range([0, iw]);
    const yMax = d3.max(series, s => d3.max(s, d => d[1])) ?? 100;
    const y = d3.scaleLinear().domain([0, yMax]).nice().range([ih, 0]);

    const area = d3.area<d3.SeriesPoint<Record<string, number>>>()
      .x(d => x(d.data.hour))
      .y0(d => y(d[0]))
      .y1(d => y(d[1]))
      .curve(d3.curveMonotoneX);

    series.forEach((s, i) => {
      g.append('path')
        .datum(s)
        .attr('d', area)
        .attr('fill', EXIT_COLORS[i % EXIT_COLORS.length])
        .attr('opacity', 0.7);
    });

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat(d => `${d}시`))
      .selectAll('text').attr('fill', 'var(--text-muted)').attr('font-size', 9);

    g.append('g')
      .call(d3.axisLeft(y).ticks(4).tickFormat(d => d3.format('.1s')(d as number)))
      .selectAll('text').attr('fill', 'var(--text-muted)').attr('font-size', 9);

    g.selectAll('.domain, .tick line').attr('stroke', 'var(--border)');

    const cx = x(currentHour);
    g.append('line')
      .attr('x1', cx).attr('x2', cx).attr('y1', 0).attr('y2', ih)
      .attr('stroke', 'var(--accent-amber)').attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4 2');

    const legendG = g.append('g').attr('transform', `translate(${iw + 8}, 4)`);
    exitEntries.forEach(([no], i) => {
      const ly = i * 14;
      legendG.append('rect').attr('x', 0).attr('y', ly).attr('width', 8).attr('height', 8)
        .attr('rx', 2).attr('fill', EXIT_COLORS[i % EXIT_COLORS.length]);
      legendG.append('text').attr('x', 12).attr('y', ly + 8)
        .text(`${no}번출구`).attr('fill', 'var(--text-muted)').attr('font-size', 8);
    });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    const guideLine = g.append('line').attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '3,2').style('display', 'none');
    const hoverDot = g.append('circle').attr('r', 3.5)
      .attr('fill', '#f59e0b').attr('stroke', '#0a0e1a').attr('stroke-width', 1.5).style('display', 'none');

    g.append('rect').attr('width', iw).attr('height', ih).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('mousemove', (event: MouseEvent) => {
        const [mx] = d3.pointer(event);
        const h = Math.max(0, Math.min(23, Math.round(x.invert(mx))));
        guideLine.attr('x1', x(h)).attr('x2', x(h)).style('display', null);
        const hourTotal = exitEntries.reduce((sum, [, hourly]) => sum + (hourly[h] ?? 0), 0);
        hoverDot.attr('cx', x(h)).attr('cy', y(hourTotal)).style('display', null);
        let html = `<b>${station.name} ${h}시</b><br/>합계: ${hourTotal.toLocaleString()}명`;
        exitEntries.forEach(([no, hourly]) => { html += `<br/>${no}번: ${(hourly[h] ?? 0).toLocaleString()}명`; });
        tooltip.style('opacity', '1').html(html);
        const [px, py] = d3.pointer(event, el);
        tooltip.style('left', (px + 12) + 'px').style('top', (py - 10) + 'px');
      })
      .on('mouseleave', () => {
        guideLine.style('display', 'none');
        hoverDot.style('display', 'none');
        tooltip.style('opacity', '0');
      });
  }, [station, currentHour, resizeKey]);

  if (stations.length === 0) return <div className="chart-empty">데이터 없음</div>;

  return (
    <div>
      <div className="chart-mode-btns">
        {stations.map((s, i) => (
          <button
            key={s.name}
            className={`mode-btn${selectedStation === i ? ' active' : ''}`}
            onClick={() => setSelectedStation(i)}
          >
            {s.name.replace('역', '')}
          </button>
        ))}
      </div>
      <div ref={ref} className="d3-chart" />
    </div>
  );
}
