import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { IndustrySummary } from '../api/client';
import './ChartCommon.css';

interface Props {
  industries: IndustrySummary[];
}

export default function SalaryDistributionChart({ industries }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || industries.length === 0) return;

    const top15 = industries
      .filter(d => d.avg_monthly_salary > 0)
      .slice(0, 15);

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = Math.max(200, top15.length * 22 + 50);
    const margin = { top: 8, right: 16, bottom: 28, left: 110 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const truncate = (s: string, max: number) => s.length > max ? s.slice(0, max) + '…' : s;
    const labels = top15.map(d => truncate(d.industry, 10));

    const x = d3.scaleLinear()
      .domain([0, d3.max(top15, d => d.avg_monthly_salary) ?? 1])
      .nice().range([0, iw]);
    const y = d3.scaleBand().domain(labels).range([0, ih]).padding(0.2);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(4).tickFormat(v => `${(+v / 10000).toFixed(0)}만`))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.append('g').call(d3.axisLeft(y).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');

    g.selectAll('.domain').remove();

    const colorScale = d3.scaleSequential(d3.interpolateViridis)
      .domain([0, d3.max(top15, d => d.total_employees) ?? 1]);

    g.selectAll('rect.bar')
      .data(top15)
      .join('rect')
      .attr('x', 0)
      .attr('y', (_, i) => y(labels[i])!)
      .attr('width', d => x(d.avg_monthly_salary))
      .attr('height', y.bandwidth())
      .attr('fill', d => colorScale(d.total_employees))
      .attr('rx', 2)
      .attr('opacity', 0.85)
      .style('cursor', 'pointer')
      .on('mouseover', function (event: MouseEvent, d: IndustrySummary) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('opacity', '1')
          .html(d.industry + '<br/>평균급여: ' + (d.avg_monthly_salary / 10000).toFixed(0) + '만원<br/>종업원: ' + d.total_employees + '명')
          .style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mousemove', function (event: MouseEvent) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseout', function () { tooltip.style('opacity', '0'); });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');

    g.selectAll('text.value')
      .data(top15)
      .join('text')
      .attr('class', 'value')
      .attr('x', d => x(d.avg_monthly_salary) + 4)
      .attr('y', (_, i) => y(labels[i])! + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .text(d => `${d.total_employees}명`)
      .style('font-size', '8px')
      .style('fill', '#94a3b8');
  }, [industries]);

  return <div ref={ref} className="chart-container" style={{ minHeight: 200 }} />;
}
