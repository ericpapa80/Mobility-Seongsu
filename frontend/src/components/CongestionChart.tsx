import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { RoadSegment } from '../api/client';
import { vcColor } from '../lib/colors';
import './ChartCommon.css';

interface Props {
  segments: RoadSegment[];
}

export default function CongestionChart({ segments }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || segments.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 160;
    const margin = { top: 8, right: 12, bottom: 28, left: 50 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const labels = segments.map((_, i) => `구간${i + 1}`);
    const x = d3.scaleLinear().domain([0, 1.1]).range([0, iw]);
    const y = d3.scaleBand().domain(labels).range([0, ih]).padding(0.25);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d3.format('.1f')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.append('g').call(d3.axisLeft(y).tickSize(0))
      .selectAll('text').style('font-size', '10px').style('fill', '#94a3b8');

    g.selectAll('.domain').remove();

    [0.5, 0.8, 1.0].forEach(v => {
      g.append('line')
        .attr('x1', x(v)).attr('x2', x(v))
        .attr('y1', 0).attr('y2', ih)
        .attr('stroke', v === 0.8 ? '#f59e0b' : v === 1.0 ? '#ef4444' : '#1e2d4a')
        .attr('stroke-width', 1).attr('stroke-dasharray', '3,3').attr('opacity', 0.6);
    });

    const bars = g.selectAll('rect.bar')
      .data(segments)
      .join('rect')
      .attr('x', 0)
      .attr('y', (_, i) => y(labels[i])!)
      .attr('width', d => x(d.vc))
      .attr('height', y.bandwidth())
      .attr('fill', d => {
        const c = vcColor(d.vc);
        return `rgb(${c[0]},${c[1]},${c[2]})`;
      })
      .attr('rx', 3)
      .style('cursor', 'pointer')
      .on('mouseover', function (event: MouseEvent, d: RoadSegment) {
        const nodes = bars.nodes();
        const i = nodes.indexOf(this as Element);
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('opacity', '1')
          .html(labels[i] + ': V/C ' + d.vc.toFixed(2))
          .style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mousemove', function (event: MouseEvent) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseout', function () { tooltip.style('opacity', '0'); });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
  }, [segments]);

  return <div ref={ref} className="chart-container" />;
}
