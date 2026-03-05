import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import './ChartCommon.css';

const FACTORS = [
  { factor: '교통량 ±10%', impact: 0.35 },
  { factor: '보행밀도 ±15%', impact: 0.28 },
  { factor: '사고빈도 ±20%', impact: 0.42 },
  { factor: '대중교통 배차', impact: 0.22 },
  { factor: '속도제한 변경', impact: 0.18 },
];

export default function SensitivityChart() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 130;
    const margin = { top: 8, right: 12, bottom: 8, left: 90 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear().domain([0, 0.5]).range([0, iw]);
    const y = d3.scaleBand().domain(FACTORS.map(d => d.factor)).range([0, ih]).padding(0.3);

    g.append('g').call(d3.axisLeft(y).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');
    g.selectAll('.domain').remove();

    const color = d3.scaleLinear<string>().domain([0.1, 0.3, 0.5]).range(['#10b981', '#f59e0b', '#ef4444']);

    g.selectAll('rect')
      .data(FACTORS)
      .join('rect')
      .attr('x', 0).attr('y', d => y(d.factor)!)
      .attr('width', d => x(d.impact)).attr('height', y.bandwidth())
      .attr('fill', d => color(d.impact))
      .attr('rx', 3).attr('opacity', 0.85)
      .style('cursor', 'pointer')
      .on('mouseover', function (event: MouseEvent, d: (typeof FACTORS)[number]) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('opacity', '1')
          .html(d.factor + ' → 영향도 ' + d.impact.toFixed(2))
          .style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mousemove', function (event: MouseEvent) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseout', function () { tooltip.style('opacity', '0'); });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
  }, []);

  return <div ref={ref} className="chart-container" />;
}
