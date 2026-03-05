import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { CrossAnalysisResponse } from '../api/client';
import './ChartCommon.css';

interface Props {
  data: CrossAnalysisResponse;
}

export default function CrossAnalysisChart({ data }: Props) {
  const corrRef = useRef<HTMLDivElement>(null);
  const vitalityRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    drawCorrelation();
    drawVitality();
  }, [data]);

  function drawCorrelation() {
    const el = corrRef.current;
    if (!el) return;
    const items = data.foot_store_correlation;
    if (items.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 160;
    const margin = { top: 12, right: 16, bottom: 32, left: 44 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear()
      .domain([0, d3.max(items, d => d.acost) ?? 1]).nice().range([0, iw]);
    const y = d3.scaleLinear()
      .domain([0, d3.max(items, d => d.store_count) ?? 1]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d3.format(',.0f')))
      .selectAll('text').style('font-size', '8px').style('fill', '#64748b');

    g.append('g').call(d3.axisLeft(y).ticks(5))
      .selectAll('text').style('font-size', '8px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    g.append('text')
      .attr('x', iw / 2).attr('y', ih + 26)
      .attr('text-anchor', 'middle')
      .text('보행 통행량 (acost)')
      .style('font-size', '9px').style('fill', '#94a3b8');

    g.append('text')
      .attr('transform', `translate(-32,${ih / 2}) rotate(-90)`)
      .attr('text-anchor', 'middle')
      .text('주변 상가 수')
      .style('font-size', '9px').style('fill', '#94a3b8');

    g.selectAll('circle')
      .data(items)
      .join('circle')
      .attr('cx', d => x(d.acost))
      .attr('cy', d => y(d.store_count))
      .attr('r', 4)
      .attr('fill', '#10b981')
      .attr('opacity', 0.7)
      .attr('stroke', '#10b981')
      .attr('stroke-width', 0.5);

    const tooltip1 = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('circle').style('cursor', 'pointer')
      .on('mouseenter', (_e: MouseEvent, d: { acost: number; store_count: number }) => {
        tooltip1.style('opacity', '1').html(`보행 통행량: ${d.acost.toLocaleString()}<br/>주변 상가 수: ${d.store_count}`);
      })
      .on('mousemove', (e: MouseEvent) => {
        const [mx, my] = d3.pointer(e, el);
        tooltip1.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip1.style('opacity', '0'));

    const xVals = items.map(d => d.acost);
    const yVals = items.map(d => d.store_count);
    const n = xVals.length;
    const xMean = d3.mean(xVals)!;
    const yMean = d3.mean(yVals)!;
    let num = 0, denX = 0, denY = 0;
    for (let i = 0; i < n; i++) {
      const dx = xVals[i] - xMean;
      const dy = yVals[i] - yMean;
      num += dx * dy;
      denX += dx * dx;
      denY += dy * dy;
    }
    const r = denX > 0 && denY > 0 ? num / Math.sqrt(denX * denY) : 0;

    g.append('text')
      .attr('x', iw - 4).attr('y', 12)
      .attr('text-anchor', 'end')
      .text(`r = ${r.toFixed(2)}`)
      .style('font-size', '11px')
      .style('font-weight', '600')
      .style('fill', r > 0.3 ? '#10b981' : '#94a3b8');
  }

  function drawVitality() {
    const el = vitalityRef.current;
    if (!el) return;

    const { inside, outside } = data.cluster_vitality;
    const timeKeys = Object.keys(inside.time_profile);
    const width = el.getBoundingClientRect().width || 320;
    const height = 140;
    const margin = { top: 12, right: 12, bottom: 28, left: 44 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const maxVal = d3.max([
      ...Object.values(inside.time_profile),
      ...Object.values(outside.time_profile),
    ]) ?? 1;

    const x0 = d3.scaleBand().domain(timeKeys).range([0, iw]).padding(0.2);
    const x1 = d3.scaleBand().domain(['inside', 'outside']).range([0, x0.bandwidth()]).padding(0.05);
    const y = d3.scaleLinear().domain([0, maxVal]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x0).tickSize(0))
      .selectAll('text').style('font-size', '8px').style('fill', '#94a3b8');

    g.append('g').call(d3.axisLeft(y).ticks(3).tickFormat(d3.format('~s')))
      .selectAll('text').style('font-size', '8px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    timeKeys.forEach((tk) => {
      const gg = g.append('g').attr('transform', `translate(${x0(tk)},0)`);
      gg.append('rect')
        .attr('class', 'vit-bar')
        .attr('data-label', tk + ' 클러스터내')
        .attr('data-val', inside.time_profile[tk])
        .attr('x', x1('inside')!).attr('y', y(inside.time_profile[tk]))
        .attr('width', x1.bandwidth()).attr('height', ih - y(inside.time_profile[tk]))
        .attr('fill', '#ec4899').attr('rx', 1).attr('opacity', 0.8);
      gg.append('rect')
        .attr('class', 'vit-bar')
        .attr('data-label', tk + ' 외부')
        .attr('data-val', outside.time_profile[tk])
        .attr('x', x1('outside')!).attr('y', y(outside.time_profile[tk]))
        .attr('width', x1.bandwidth()).attr('height', ih - y(outside.time_profile[tk]))
        .attr('fill', '#64748b').attr('rx', 1).attr('opacity', 0.6);
    });

    const tooltip2 = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('.vit-bar').style('cursor', 'pointer')
      .on('mouseenter', function () {
        const label = d3.select(this).attr('data-label');
        const val = d3.select(this).attr('data-val');
        tooltip2.style('opacity', '1').html(`<b>${label}</b><br/>매출: ${Number(val).toLocaleString()}만원`);
      })
      .on('mousemove', function (event: MouseEvent) {
        const [mx, my] = d3.pointer(event, el);
        tooltip2.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip2.style('opacity', '0'));

    const legend = svg.append('g').attr('transform', `translate(${margin.left + iw - 110},${margin.top - 2})`);
    [{ label: `클러스터 내 (${inside.count})`, color: '#ec4899' }, { label: `외부 (${outside.count})`, color: '#64748b' }].forEach((d, i) => {
      const row = legend.append('g').attr('transform', `translate(${i * 80},0)`);
      row.append('rect').attr('width', 8).attr('height', 8).attr('rx', 1).attr('fill', d.color);
      row.append('text').attr('x', 10).attr('y', 8).text(d.label)
        .style('font-size', '8px').style('fill', '#94a3b8');
    });
  }

  return (
    <div>
      <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 4, fontWeight: 600 }}>
        보행-상권 상관 (상위 50 링크 반경 50m)
      </div>
      <div ref={corrRef} className="chart-container" style={{ minHeight: 160 }} />
      <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 4, marginTop: 12, fontWeight: 600 }}>
        크래프톤 클러스터 내/외 시간대별 방문
      </div>
      <div ref={vitalityRef} className="chart-container" style={{ minHeight: 140 }} />
    </div>
  );
}
