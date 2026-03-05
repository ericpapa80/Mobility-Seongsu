import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import type { Store } from '../api/client';
import type { StoreSettings } from './Sidebar';
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

const KEYS = ['평일', '공휴일'];
const CAT_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};

export default function StoreRevfreqChart({ stores, settings }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const containerWidth = useContainerWidth(ref);

  const filtered = useMemo(
    () => stores.filter(s => settings.categories.includes(s.category_bg)),
    [stores, settings.categories],
  );

  const data = useMemo(() => {
    return settings.categories.map(cat => {
      const catStores = filtered.filter(s => s.category_bg === cat);
      const n = catStores.length || 1;
      const weekday = catStores.reduce((s, st) => s + (st.revfreq_weekday ?? 0), 0) / n;
      const holiday = catStores.reduce((s, st) => s + (st.revfreq_holiday ?? 0), 0) / n;
      return { cat, values: [weekday, holiday] };
    });
  }, [filtered, settings.categories]);

  useEffect(() => {
    const el = ref.current;
    if (!el || data.length === 0) return;

    const width = containerWidth || el.getBoundingClientRect().width || 340;
    const height = 180;
    const margin = { top: 22, right: 12, bottom: 28, left: 52 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x0 = d3.scaleBand().domain(KEYS).range([0, iw]).padding(0.3);
    const x1 = d3.scaleBand().domain(settings.categories).range([0, x0.bandwidth()]).padding(0.05);
    const allMax = d3.max(data, d => d3.max(d.values)) ?? 1;
    const y = d3.scaleLinear().domain([0, allMax]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x0).tickSize(0))
      .selectAll('text').style('font-size', '10px').style('fill', '#94a3b8');
    g.append('g')
      .call(d3.axisLeft(y).ticks(5))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');
    g.selectAll('.domain').remove();

    data.forEach(({ cat, values }) => {
      const color = CAT_COLORS[cat] ?? '#94a3b8';
      values.forEach((v, i) => {
        const barG = g.append('g');
        barG.append('rect')
          .attr('x', x0(KEYS[i])! + (x1(cat) ?? 0))
          .attr('y', y(v)).attr('width', x1.bandwidth()).attr('height', ih - y(v))
          .attr('fill', color).attr('rx', 2).attr('opacity', 0.85);
        barG.append('text')
          .attr('x', x0(KEYS[i])! + (x1(cat) ?? 0) + x1.bandwidth() / 2)
          .attr('y', y(v) - 3).attr('text-anchor', 'middle')
          .text(v > 0 ? v.toFixed(1) : '')
          .style('font-size', '8px').style('fill', '#94a3b8');
      });
    });

    const legend = svg.append('g').attr('transform', `translate(${margin.left + iw - settings.categories.length * 50},2)`);
    settings.categories.forEach((cat, i) => {
      legend.append('rect').attr('x', i * 50).attr('y', 0).attr('width', 8).attr('height', 8)
        .attr('fill', CAT_COLORS[cat] ?? '#94a3b8').attr('rx', 2);
      legend.append('text').attr('x', i * 50 + 11).attr('y', 8)
        .text(cat).style('font-size', '9px').style('fill', '#94a3b8');
    });
  }, [data, containerWidth, settings.categories]);

  return <div ref={ref} className="chart-container" style={{ minHeight: 180 }} />;
}
