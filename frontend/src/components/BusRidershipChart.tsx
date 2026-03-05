import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { BusStopHourly } from '../api/client';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

interface Props {
  stops: BusStopHourly[];
  mode: 'ride' | 'alight' | 'total';
}

export default function BusRidershipChart({ stops, mode }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(ref);

  useEffect(() => {
    const el = ref.current;
    if (!el || stops.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 180;
    const margin = { top: 12, right: 12, bottom: 28, left: 44 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const top10 = [...stops].sort((a, b) => (b.ride + b.alight) - (a.ride + a.alight)).slice(0, 10);
    const values = top10.map(s => mode === 'ride' ? s.ride : mode === 'alight' ? s.alight : s.ride + s.alight);
    const names = top10.map(s => s.name.length > 6 ? s.name.slice(0, 6) + '…' : s.name);

    const x = d3.scaleBand().domain(names).range([0, iw]).padding(0.3);
    const y = d3.scaleLinear().domain([0, d3.max(values) ?? 1]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).tickSize(0))
      .selectAll('text').style('font-size', '8px').style('fill', '#94a3b8')
      .attr('transform', 'rotate(-30)').attr('text-anchor', 'end');

    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d3.format(',.0f')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    const color = mode === 'ride' ? '#06b6d4' : mode === 'alight' ? '#ec4899' : '#3b82f6';

    g.selectAll('rect')
      .data(values)
      .join('rect')
      .attr('x', (_, i) => x(names[i])!)
      .attr('y', d => y(d))
      .attr('width', x.bandwidth())
      .attr('height', d => ih - y(d))
      .attr('fill', color)
      .attr('rx', 3)
      .attr('opacity', 0.85)
      .style('cursor', 'pointer');

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect')
      .on('mouseenter', function(_e: MouseEvent, d: number) {
        const idx = g.selectAll('rect').nodes().indexOf(this);
        const label = mode === 'ride' ? '승차' : mode === 'alight' ? '하차' : '합계';
        tooltip.style('opacity', '1').html(`<b>${names[idx]}</b><br/>${label}: ${d.toLocaleString()}명`);
      })
      .on('mousemove', (event: MouseEvent) => {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));
  }, [stops, mode, resizeKey]);

  return <div ref={ref} className="chart-container" />;
}
