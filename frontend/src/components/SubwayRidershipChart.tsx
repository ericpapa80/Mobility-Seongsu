import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { SubwayStationHourly } from '../api/client';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

export type RidershipMode = 'ridealight' | 'foreign';

interface Props {
  stations: SubwayStationHourly[];
  mode: RidershipMode;
  currentHour: number;
}

const RIDE_ALIGHT_SERIES = [
  { key: 'ride', label: '승차', color: '#3b82f6' },
  { key: 'alight', label: '하차', color: '#f59e0b' },
];

const FOREIGN_SERIES = [
  { key: 'f_ride', label: '외국인 승차', color: '#ef4444' },
  { key: 'f_alight', label: '외국인 하차', color: '#f59e0b' },
];

export default function SubwayRidershipChart({ stations, mode, currentHour }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(ref);
  const [selectedStation, setSelectedStation] = useState(-1);

  const isForeignMode = mode === 'foreign';
  const availableStations = isForeignMode
    ? stations.filter(s => !s.name.includes('서울숲'))
    : stations;

  const safeSelected = (() => {
    if (selectedStation < 0) return -1;
    const orig = stations[selectedStation];
    if (!orig) return -1;
    if (isForeignMode && orig.name.includes('서울숲')) return -1;
    return selectedStation;
  })();

  const targetStations = safeSelected < 0 ? availableStations : [stations[safeSelected]];

  useEffect(() => {
    const el = ref.current;
    if (!el || targetStations.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 240;
    const margin = { top: 28, right: 12, bottom: 28, left: 44 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('svg,.chart-tip').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const hours = d3.range(24);
    const isForeign = isForeignMode;
    const activeSeries = isForeign ? FOREIGN_SERIES : RIDE_ALIGHT_SERIES;

    const aggregated = hours.map(h => {
      const obj: Record<string, number> = { hour: h };
      if (isForeign) {
        let rideTotal = 0;
        let alightTotal = 0;
        for (const stn of targetStations) {
          const fh = stn.by_user_group['foreign'];
          if (fh) {
            const sum = stn.ridership.ride[h] + stn.ridership.alight[h];
            const rideR = stn.ridership.ride[h] / Math.max(sum, 1);
            rideTotal += Math.round(fh[h] * rideR);
            alightTotal += Math.round(fh[h] * (1 - rideR));
          }
        }
        obj['f_ride'] = rideTotal;
        obj['f_alight'] = alightTotal;
      } else {
        let rideTotal = 0;
        let alightTotal = 0;
        for (const stn of targetStations) {
          rideTotal += stn.ridership.ride[h];
          alightTotal += stn.ridership.alight[h];
        }
        obj['ride'] = rideTotal;
        obj['alight'] = alightTotal;
      }
      return obj;
    });

    const keys = activeSeries.map(s => s.key);
    const stack = d3.stack<Record<string, number>>().keys(keys).order(d3.stackOrderNone).offset(d3.stackOffsetNone);
    const series = stack(aggregated);
    const seriesColors = activeSeries.map(s => s.color);

    const x = d3.scaleBand<number>().domain(hours).range([0, iw]).padding(0.15);
    const yMax = d3.max(series, s => d3.max(s, d => d[1])) ?? 100;
    const y = d3.scaleLinear().domain([0, yMax]).nice().range([ih, 0]);

    series.forEach((s, i) => {
      g.selectAll(`.bar-${keys[i]}`)
        .data(s)
        .join('rect')
        .attr('x', d => x(d.data.hour as number)!)
        .attr('y', d => y(d[1]))
        .attr('height', d => y(d[0]) - y(d[1]))
        .attr('width', x.bandwidth())
        .attr('fill', seriesColors[i])
        .attr('opacity', d => d.data.hour === currentHour ? 1 : 0.7)
        .attr('rx', 1);
    });

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).tickValues([0, 4, 8, 12, 16, 20]).tickFormat(d => `${d}시`))
      .selectAll('text').attr('fill', 'var(--text-muted)').attr('font-size', 9);

    g.append('g')
      .call(d3.axisLeft(y).ticks(4).tickFormat(d => d3.format('.1s')(d as number)))
      .selectAll('text').attr('fill', 'var(--text-muted)').attr('font-size', 9);

    g.selectAll('.domain, .tick line').attr('stroke', 'var(--border)');

    const currentX = (x(currentHour) ?? 0) + x.bandwidth() / 2;
    g.append('line')
      .attr('x1', currentX).attr('x2', currentX).attr('y1', 0).attr('y2', ih)
      .attr('stroke', 'var(--accent-amber)').attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4 2');

    const legendG = g.append('g').attr('transform', `translate(0, -18)`);
    activeSeries.forEach((item, i) => {
      const lx = i * (isForeign ? 80 : 52);
      legendG.append('rect').attr('x', lx).attr('y', 0).attr('width', 8).attr('height', 8)
        .attr('rx', 2).attr('fill', item.color);
      legendG.append('text').attr('x', lx + 11).attr('y', 8)
        .text(item.label).attr('fill', 'var(--text-muted)').attr('font-size', 8);
    });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    const guideLine = g.append('line').attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '3,2').style('display', 'none');

    g.append('rect').attr('width', iw).attr('height', ih).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('mousemove', (event: MouseEvent) => {
        const [mx] = d3.pointer(event);
        const domain = x.domain();
        const step = x.step();
        const h = domain[Math.max(0, Math.min(domain.length - 1, Math.floor(mx / step)))];
        const cx = (x(h) ?? 0) + x.bandwidth() / 2;
        guideLine.attr('x1', cx).attr('x2', cx).style('display', null);
        let html = `<b>${h}시</b>`;
        activeSeries.forEach(s => { html += `<br/>${s.label}: ${(aggregated[h][s.key]).toLocaleString()}명`; });
        tooltip.style('opacity', '1').html(html);
        const [px, py] = d3.pointer(event, el);
        tooltip.style('left', (px + 12) + 'px').style('top', (py - 10) + 'px');
      })
      .on('mouseleave', () => {
        guideLine.style('display', 'none');
        tooltip.style('opacity', '0');
      });
  }, [targetStations, mode, currentHour, resizeKey]);

  if (stations.length === 0) return <div className="chart-empty">데이터 없음</div>;

  return (
    <div>
      <div className="chart-mode-btns">
        <button
          className={`mode-btn${safeSelected < 0 ? ' active' : ''}`}
          onClick={() => setSelectedStation(-1)}
        >
          전체
        </button>
        {stations.map((s, i) => {
          if (isForeignMode && s.name.includes('서울숲')) return null;
          return (
            <button
              key={s.name}
              className={`mode-btn${safeSelected === i ? ' active' : ''}`}
              onClick={() => setSelectedStation(i)}
            >
              {s.name.replace('역', '')}
            </button>
          );
        })}
      </div>
      <div ref={ref} className="d3-chart" />
    </div>
  );
}
