import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import type { Store } from '../api/client';
import type { StoreSettings } from './Sidebar';
import { fmtWon, fmtAxisWon } from '../lib/format';
import './ChartCommon.css';

function useContainerWidth(ref: React.RefObject<HTMLDivElement | null>) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const cr = entries[0]?.contentRect;
      if (cr) setW(Math.round(cr.width));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  return w;
}

interface Props {
  stores: Store[];
  settings: StoreSettings;
}

const CAT_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};
const YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025];

export default function StoreTrendChart({ stores, settings }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const containerWidth = useContainerWidth(ref);

  const filtered = useMemo(
    () => stores.filter(s => settings.categories.includes(s.category_bg)),
    [stores, settings.categories],
  );

  const lineData = useMemo(() => {
    return settings.categories.map(cat => {
      const values = YEARS.map(yr => {
        let sum = 0;
        for (const s of filtered) {
          if (s.category_bg !== cat || !s.trend) continue;
          const t = s.trend.find(t => t.year === yr);
          if (t) sum += t.store;
        }
        return sum;
      });
      return { cat, values };
    });
  }, [filtered, settings.categories]);

  useEffect(() => {
    const el = ref.current;
    if (!el || lineData.length === 0) return;

    const width = containerWidth || el.getBoundingClientRect().width || 340;
    const height = 220;
    const margin = { top: 22, right: 12, bottom: 28, left: 56 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scalePoint().domain(YEARS.map(String)).range([0, iw]).padding(0.3);
    const allMax = d3.max(lineData, d => d3.max(d.values)) ?? 1;
    const y = d3.scaleLinear().domain([0, allMax]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).tickSize(0))
      .selectAll('text').style('font-size', '8px').style('fill', '#94a3b8');
    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(fmtAxisWon))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');
    g.selectAll('.domain').remove();

    const line = d3.line<number>()
      .x((_, i) => x(String(YEARS[i]))!)
      .y(d => y(d))
      .curve(d3.curveMonotoneX);

    lineData.forEach(({ cat, values }) => {
      const color = CAT_COLORS[cat] ?? '#94a3b8';
      g.append('path').datum(values)
        .attr('fill', 'none').attr('stroke', color).attr('stroke-width', 2).attr('d', line);
      g.selectAll(`.dot-${cat}`).data(values).join('circle')
        .attr('cx', (_, i) => x(String(YEARS[i]))!)
        .attr('cy', d => y(d))
        .attr('r', 3).attr('fill', color)
        .attr('stroke', '#1e293b').attr('stroke-width', 1)
        .attr('data-cat', cat)
        .attr('data-year', (_, i) => YEARS[i]);
    });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('circle').style('cursor', 'pointer')
      .on('mouseenter', function(_e, d) {
        const cat = d3.select(this).attr('data-cat');
        const yr = d3.select(this).attr('data-year');
        tooltip.style('opacity', '1').html(`<b>${yr}년</b><br/>${cat}: ${fmtWon(d as number)}원`);
      })
      .on('mousemove', function(event: MouseEvent) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    const legend = svg.append('g').attr('transform', `translate(${margin.left + iw - settings.categories.length * 50},2)`);
    settings.categories.forEach((cat, i) => {
      legend.append('rect').attr('x', i * 50).attr('y', 0).attr('width', 8).attr('height', 8)
        .attr('fill', CAT_COLORS[cat] ?? '#94a3b8').attr('rx', 2);
      legend.append('text').attr('x', i * 50 + 11).attr('y', 8)
        .text(cat).style('font-size', '9px').style('fill', '#94a3b8');
    });
  }, [lineData, containerWidth, settings.categories]);

  return <div ref={ref} className="chart-container" style={{ minHeight: 220 }} />;
}
