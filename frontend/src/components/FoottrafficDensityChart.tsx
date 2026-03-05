import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { FoottrafficResponse } from '../api/client';
import type { FoottrafficSettings } from './Sidebar';
import { HOUR_TO_TMZON } from '../lib/layer_colors';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

interface Props {
  data: FoottrafficResponse;
  currentHour: number;
  settings: FoottrafficSettings;
}

const TMZON_ORDER = ['00~05', '06~10', '11~13', '14~16', '17~20', '21~23'];

export default function FoottrafficDensityChart({ data, currentHour, settings }: Props) {
  const barRef = useRef<HTMLDivElement>(null);
  const gradeRef = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(barRef);

  const { dayweek, agrde } = settings;
  const currentTmzon = HOUR_TO_TMZON[currentHour];
  const dayLabel = dayweek === '1' ? '평일' : '주말';
  const agrLabel = agrde === '00' ? '전체' : `${agrde}대`;

  useEffect(() => {
    const el = barRef.current;
    if (!el || data.links.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 140;
    const margin = { top: 8, right: 16, bottom: 28, left: 52 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const totalsByTmzon = TMZON_ORDER.map(tz => {
      let sum = 0;
      for (const link of data.links) {
        sum += link.data?.[dayweek]?.[agrde]?.[tz]?.acost ?? 0;
      }
      return { tmzon: tz, total: sum };
    });

    const x = d3.scaleBand().domain(TMZON_ORDER).range([0, iw]).padding(0.15);
    const y = d3.scaleLinear().domain([0, d3.max(totalsByTmzon, d => d.total) ?? 1]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).tickSize(0))
      .selectAll('text').style('font-size', '8px').style('fill', '#94a3b8');

    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d3.format('~s')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    g.selectAll('rect.bar')
      .data(totalsByTmzon)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.tmzon)!)
      .attr('y', d => y(d.total))
      .attr('width', x.bandwidth())
      .attr('height', d => ih - y(d.total))
      .attr('fill', d => d.tmzon === currentTmzon ? '#f59e0b' : '#3b82f6')
      .attr('rx', 3)
      .attr('opacity', d => d.tmzon === currentTmzon ? 1 : 0.6);

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect.bar').style('cursor', 'pointer')
      .on('mouseenter', (_e: MouseEvent, d: { tmzon: string; total: number }) => {
        tooltip.style('opacity', '1').html(`<b>${d.tmzon}</b><br/>통행량: ${d.total.toLocaleString()}`);
      })
      .on('mousemove', (e: MouseEvent) => {
        const [mx, my] = d3.pointer(e, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));
  }, [data, currentHour, dayweek, agrde, currentTmzon, resizeKey]);

  useEffect(() => {
    const el = gradeRef.current;
    if (!el || data.links.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 140;
    const margin = { top: 8, right: 16, bottom: 24, left: 52 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const gradeCounts = [0, 0, 0, 0, 0];
    for (const link of data.links) {
      const grade = link.data?.[dayweek]?.[agrde]?.[currentTmzon]?.grade;
      if (grade && grade >= 1 && grade <= 5) {
        gradeCounts[grade - 1]++;
      }
    }
    const gradeData = gradeCounts.map((count, i) => ({ grade: i + 1, count }));
    const gradeLabels = gradeData.map(d => `등급${d.grade}`);

    const x = d3.scaleLinear().domain([0, d3.max(gradeData, d => d.count) ?? 1]).nice().range([0, iw]);
    const y = d3.scaleBand().domain(gradeLabels).range([0, ih]).padding(0.2);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(4).tickFormat(d3.format(',.0f')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.append('g').call(d3.axisLeft(y).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');

    g.selectAll('.domain').remove();

    const gradeColors = ['#00682c', '#31a354', '#ffff00', '#ff7f00', '#ff0000'];
    g.selectAll('rect.grade-bar')
      .data(gradeData)
      .join('rect')
      .attr('class', 'grade-bar')
      .attr('x', 0)
      .attr('y', d => y(`등급${d.grade}`)!)
      .attr('width', d => x(d.count))
      .attr('height', y.bandwidth())
      .attr('fill', d => gradeColors[d.grade - 1])
      .attr('rx', 2)
      .attr('opacity', 0.85);

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect.grade-bar').style('cursor', 'pointer')
      .on('mouseenter', (_e: MouseEvent, d: { grade: number; count: number }) => {
        tooltip.style('opacity', '1').html(`<b>등급 ${d.grade}</b><br/>구간 수: ${d.count}`);
      })
      .on('mousemove', (e: MouseEvent) => {
        const [mx, my] = d3.pointer(e, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));
  }, [data, currentHour, dayweek, agrde, currentTmzon, resizeKey]);

  return (
    <div>
      <div ref={barRef} className="chart-container" style={{ minHeight: 140 }} />
      <div style={{
        fontSize: 10,
        color: '#94a3b8',
        padding: '8px 0 6px 52px',
        marginTop: 8,
        borderTop: '1px solid var(--border)',
      }}>
        등급별 구간 수 ({dayLabel} · {agrLabel} · {currentTmzon})
      </div>
      <div ref={gradeRef} className="chart-container" style={{ minHeight: 140 }} />
    </div>
  );
}
