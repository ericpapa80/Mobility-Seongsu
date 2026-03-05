import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

function generateHourlyData() {
  return Array.from({ length: 24 }, (_, i) => {
    let val = 500;
    if (i >= 7 && i <= 9) val = 2000 + Math.random() * 800;
    else if (i >= 11 && i <= 14) val = 2500 + Math.random() * 1000;
    else if (i >= 17 && i <= 20) val = 3000 + Math.random() * 1200;
    else if (i >= 21 || i <= 5) val = 300 + Math.random() * 400;
    else val = 1000 + Math.random() * 600;
    return { hour: i, density: Math.round(val), prev: Math.round(val * (0.85 + Math.random() * 0.3)) };
  });
}

interface Props {
  currentHour: number;
}

export default function PedDensityTrendChart({ currentHour }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(ref);
  const data = useMemo(generateHourlyData, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 170;
    const margin = { top: 12, right: 12, bottom: 28, left: 40 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear().domain([0, 23]).range([0, iw]);
    const yMax = d3.max(data, d => Math.max(d.density, d.prev)) ?? 1;
    const y = d3.scaleLinear().domain([0, yMax * 1.1]).range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(8).tickFormat(d => `${d}시`))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('.0s')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    const areaPrev = d3.area<typeof data[0]>()
      .x(d => x(d.hour)).y0(ih).y1(d => y(d.prev))
      .curve(d3.curveMonotoneX);

    const areaCurr = d3.area<typeof data[0]>()
      .x(d => x(d.hour)).y0(ih).y1(d => y(d.density))
      .curve(d3.curveMonotoneX);

    const lineCurr = d3.line<typeof data[0]>()
      .x(d => x(d.hour)).y(d => y(d.density))
      .curve(d3.curveMonotoneX);

    g.append('path').datum(data)
      .attr('fill', 'rgba(100,116,139,0.1)')
      .attr('d', areaPrev);

    g.append('path').datum(data)
      .attr('fill', 'rgba(6,182,212,0.15)')
      .attr('d', areaCurr);

    g.append('path').datum(data)
      .attr('fill', 'none')
      .attr('stroke', '#06b6d4')
      .attr('stroke-width', 2)
      .attr('d', lineCurr);

    g.selectAll('circle')
      .data(data.filter((_, i) => i % 3 === 0))
      .join('circle')
      .attr('cx', d => x(d.hour))
      .attr('cy', d => y(d.density))
      .attr('r', 3)
      .attr('fill', '#06b6d4')
      .attr('stroke', '#0a0e1a')
      .attr('stroke-width', 1.5);

    g.append('line')
      .attr('x1', x(currentHour)).attr('x2', x(currentHour))
      .attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#f59e0b').attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,3').attr('opacity', 0.7);

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
        hoverDot.attr('cx', x(h)).attr('cy', y(data[h].density)).style('display', null);
        tooltip.style('opacity', '1').html(
          `<b>${h}시</b><br/>이번 달: ${data[h].density.toLocaleString()}<br/>전월: ${data[h].prev.toLocaleString()}`
        );
        const [px, py] = d3.pointer(event, el);
        tooltip.style('left', (px + 12) + 'px').style('top', (py - 10) + 'px');
      })
      .on('mouseleave', () => {
        guideLine.style('display', 'none');
        hoverDot.style('display', 'none');
        tooltip.style('opacity', '0');
      });

    const legend = svg.append('g').attr('transform', `translate(${width - 130}, 4)`);
    legend.append('line').attr('x1', 0).attr('x2', 16).attr('y1', 4).attr('y2', 4)
      .attr('stroke', '#06b6d4').attr('stroke-width', 2);
    legend.append('text').attr('x', 20).attr('y', 8).text('이번 달')
      .style('font-size', '9px').style('fill', '#94a3b8');
    legend.append('line').attr('x1', 60).attr('x2', 76).attr('y1', 4).attr('y2', 4)
      .attr('stroke', '#64748b').attr('stroke-width', 1).attr('stroke-dasharray', '3,2');
    legend.append('text').attr('x', 80).attr('y', 8).text('전월')
      .style('font-size', '9px').style('fill', '#64748b');
  }, [data, currentHour, resizeKey]);

  return <div ref={ref} className="chart-container" />;
}
