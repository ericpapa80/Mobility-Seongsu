import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { Workplace, GeoJSONCollection } from '../api/client';
import { extractAreas, findArea } from '../lib/geo';
import './ChartCommon.css';

interface Props {
  workplaces: Workplace[];
  commercialAreaGeoJson: GeoJSONCollection;
}

interface AreaStats {
  name: string;
  count: number;
  totalEmployees: number;
  avgSalary: number;
}

const BAR_COUNT_COLOR = '#3b82f6';
const BAR_SALARY_COLOR = '#10b981';

export default function AreaWorkplaceChart({ workplaces, commercialAreaGeoJson }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const areas = useMemo(
    () => extractAreas(commercialAreaGeoJson),
    [commercialAreaGeoJson],
  );

  const grouped = useMemo(() => {
    const map = new Map<string, { count: number; totalEmployees: number; totalSalary: number }>();

    for (const wp of workplaces) {
      const areaName = findArea(wp.lng, wp.lat, areas);
      const cur = map.get(areaName);
      if (!cur) {
        map.set(areaName, {
          count: 1,
          totalEmployees: wp.employees,
          totalSalary: wp.monthly_salary * wp.employees,
        });
      } else {
        cur.count += 1;
        cur.totalEmployees += wp.employees;
        cur.totalSalary += wp.monthly_salary * wp.employees;
      }
    }

    return [...map.entries()]
      .map(([name, v]) => ({
        name,
        count: v.count,
        totalEmployees: v.totalEmployees,
        avgSalary: v.totalEmployees > 0 ? v.totalSalary / v.totalEmployees : 0,
      }))
      .sort((a, b) => b.count - a.count);
  }, [workplaces, areas]);

  useEffect(() => {
    const el = ref.current;
    if (!el || grouped.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 240;
    const margin = { top: 10, right: 50, bottom: 36, left: 82 };
    const barH = 18;
    const ih = grouped.length * (barH + 4);
    const chartHeight = Math.min(height - margin.top - margin.bottom, ih);
    const iw = width - margin.left - margin.right;

    d3.select(el).selectAll('*').remove();

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');

    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const y = d3
      .scaleBand()
      .domain(grouped.map((d) => d.name))
      .range([0, chartHeight])
      .padding(0.25);

    const yInner = d3
      .scaleBand()
      .domain(['count', 'salary'] as const)
      .range([0, y.bandwidth()])
      .padding(0.15);

    const maxCount = d3.max(grouped, (d) => d.count) ?? 1;
    const maxSalary = d3.max(grouped, (d) => d.avgSalary) ?? 1;
    const x = d3.scaleLinear().domain([0, 1]).range([0, iw]);

    g.append('g')
      .call(d3.axisLeft(y).tickSize(0))
      .selectAll('text')
      .style('font-size', '10px')
      .style('fill', '#cbd5e1');

    g.append('g')
      .attr('transform', `translate(0,${chartHeight})`)
      .call(d3.axisBottom(x).ticks(4).tickFormat((v) => `${Math.round(+v * 100)}%`))
      .selectAll('text')
      .style('font-size', '9px')
      .style('fill', '#94a3b8');

    g.selectAll('.domain').remove();

    const showTip = (event: MouseEvent, d: AreaStats) => {
      const [mx, my] = d3.pointer(event, el);
      tooltip
        .style('opacity', '1')
        .style('left', `${mx + 12}px`)
        .style('top', `${my - 10}px`)
        .html(
          `<b>${d.name}</b><br/>사업장: ${d.count.toLocaleString()}개<br/>종업원: ${d.totalEmployees.toLocaleString()}명<br/>평균 급여: ${(d.avgSalary / 10_000).toFixed(1)}만원`,
        );
    };

    grouped.forEach((d) => {
      const yy = y(d.name)!;
      const countNorm = maxCount > 0 ? d.count / maxCount : 0;
      const salaryNorm = maxSalary > 0 ? d.avgSalary / maxSalary : 0;
      const countW = x(countNorm);
      const salaryW = x(salaryNorm);

      const countG = g
        .append('g')
        .attr('transform', `translate(0,${yy + yInner('count')!})`)
        .attr('data-area', d.name);
      countG
        .append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', countW)
        .attr('height', yInner.bandwidth())
        .attr('fill', BAR_COUNT_COLOR)
        .attr('rx', 2)
        .style('cursor', 'pointer')
        .on('mouseenter', (event: MouseEvent) => showTip(event, d))
        .on('mousemove', (event: MouseEvent) => {
          const [mx, my] = d3.pointer(event, el);
          tooltip.style('left', `${mx + 12}px`).style('top', `${my - 10}px`);
        })
        .on('mouseleave', () => tooltip.style('opacity', '0'));

      const salaryG = g
        .append('g')
        .attr('transform', `translate(0,${yy + yInner('salary')!})`)
        .attr('data-area', d.name);
      salaryG
        .append('rect')
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', salaryW)
        .attr('height', yInner.bandwidth())
        .attr('fill', BAR_SALARY_COLOR)
        .attr('rx', 2)
        .style('cursor', 'pointer')
        .on('mouseenter', (event: MouseEvent) => showTip(event, d))
        .on('mousemove', (event: MouseEvent) => {
          const [mx, my] = d3.pointer(event, el);
          tooltip.style('left', `${mx + 12}px`).style('top', `${my - 10}px`);
        })
        .on('mouseleave', () => tooltip.style('opacity', '0'));
    });

    const legendY = height - 16;
    const gLegend = svg.append('g').attr('transform', `translate(${margin.left},${legendY})`);
    const lg1 = gLegend.append('g').attr('transform', 'translate(0,0)');
    lg1.append('rect').attr('width', 10).attr('height', 8).attr('rx', 2).attr('fill', BAR_COUNT_COLOR);
    lg1.append('text').attr('x', 14).attr('y', 6).text('사업장 수').style('font-size', '9px').style('fill', '#94a3b8');
    const lg2 = gLegend.append('g').attr('transform', 'translate(80,0)');
    lg2.append('rect').attr('width', 10).attr('height', 8).attr('rx', 2).attr('fill', BAR_SALARY_COLOR);
    lg2.append('text').attr('x', 14).attr('y', 6).text('평균 급여').style('font-size', '9px').style('fill', '#94a3b8');
  }, [grouped]);

  if (grouped.length === 0) return null;

  return <div ref={ref} className="chart-container" style={{ minHeight: 240 }} />;
}
