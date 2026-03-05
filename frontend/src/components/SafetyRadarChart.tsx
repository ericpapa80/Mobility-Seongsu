import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import './ChartCommon.css';

const METRICS = [
  { axis: '교통사고', value: 0.75 },
  { axis: '보행안전', value: 0.82 },
  { axis: '야간조명', value: 0.65 },
  { axis: 'CCTV 밀도', value: 0.70 },
  { axis: '도로상태', value: 0.88 },
  { axis: '속도위반', value: 0.60 },
];

export default function SafetyRadarChart() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const size = Math.min(rect.width || 300, 220);
    const cx = size / 2;
    const cy = size / 2;
    const r = size / 2 - 30;
    const n = METRICS.length;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', size).attr('height', size);
    const g = svg.append('g');

    const angleSlice = (Math.PI * 2) / n;

    [0.25, 0.5, 0.75, 1].forEach(level => {
      const pts = METRICS.map((_, i) => {
        const a = angleSlice * i - Math.PI / 2;
        return `${cx + r * level * Math.cos(a)},${cy + r * level * Math.sin(a)}`;
      });
      g.append('polygon')
        .attr('points', pts.join(' '))
        .attr('fill', 'none').attr('stroke', '#1e2d4a').attr('stroke-width', 1);
    });

    METRICS.forEach((_, i) => {
      const a = angleSlice * i - Math.PI / 2;
      g.append('line')
        .attr('x1', cx).attr('y1', cy)
        .attr('x2', cx + r * Math.cos(a)).attr('y2', cy + r * Math.sin(a))
        .attr('stroke', '#1e2d4a').attr('stroke-width', 1);
    });

    const dataPoints = METRICS.map((d, i) => {
      const a = angleSlice * i - Math.PI / 2;
      return [cx + r * d.value * Math.cos(a), cy + r * d.value * Math.sin(a)] as [number, number];
    });

    const area = d3.line<[number, number]>().x(d => d[0]).y(d => d[1]).curve(d3.curveLinearClosed);

    g.append('path')
      .datum(dataPoints)
      .attr('d', area)
      .attr('fill', 'rgba(59,130,246,0.2)')
      .attr('stroke', '#3b82f6').attr('stroke-width', 2);

    g.selectAll('circle.radar-dot')
      .data(METRICS)
      .join('circle')
      .attr('class', 'radar-dot')
      .attr('cx', (_, i) => dataPoints[i][0])
      .attr('cy', (_, i) => dataPoints[i][1])
      .attr('r', 3)
      .attr('fill', '#3b82f6')
      .attr('stroke', 'white')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer');

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('circle.radar-dot')
      .on('mouseenter', (_e: MouseEvent, d: typeof METRICS[0]) => {
        tooltip.style('opacity', '1').html(`<b>${d.axis}</b><br/>점수: ${(d.value * 100).toFixed(0)}%`);
      })
      .on('mousemove', (e: MouseEvent) => {
        const [mx, my] = d3.pointer(e, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    METRICS.forEach((d, i) => {
      const a = angleSlice * i - Math.PI / 2;
      const lx = cx + (r + 16) * Math.cos(a);
      const ly = cy + (r + 16) * Math.sin(a);
      g.append('text')
        .attr('x', lx).attr('y', ly)
        .attr('text-anchor', 'middle').attr('dy', '0.35em')
        .text(d.axis)
        .style('font-size', '9px').style('fill', '#94a3b8').style('font-weight', '500');
    });
  }, []);

  return <div ref={ref} className="chart-container" style={{ display: 'flex', justifyContent: 'center' }} />;
}
