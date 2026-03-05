import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import type { Store } from '../api/client';
import type { StoreSettings } from './Sidebar';
import { fmtWon } from '../lib/format';
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

const PECO_KEYS = ['개인', '법인', '외국인'] as const;
const PECO_COLORS = ['#10b981', '#3b82f6', '#f59e0b'];

export default function StorePecoChart({ stores, settings }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const containerWidth = useContainerWidth(ref);

  const filtered = useMemo(
    () => stores.filter(s => settings.categories.includes(s.category_bg)),
    [stores, settings.categories],
  );

  const pieData = useMemo(() => {
    let individual = 0, corporate = 0, foreign = 0;
    for (const s of filtered) {
      individual += s.peco_individual;
      corporate += s.peco_corporate;
      foreign += s.peco_foreign;
    }
    return [
      { label: '개인', value: individual, color: PECO_COLORS[0] },
      { label: '법인', value: corporate, color: PECO_COLORS[1] },
      { label: '외국인', value: foreign, color: PECO_COLORS[2] },
    ].filter(d => d.value > 0);
  }, [filtered]);

  useEffect(() => {
    const el = ref.current;
    if (!el || pieData.length === 0) return;

    const width = containerWidth || el.getBoundingClientRect().width || 340;
    const height = 180;
    const radius = Math.min(width, height) / 2 - 40;
    const cx = width * 0.38;
    const cy = height / 2;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${cx},${cy})`);

    const pie = d3.pie<typeof pieData[0]>().value(d => d.value).sort(null);
    const arc = d3.arc<d3.PieArcDatum<typeof pieData[0]>>()
      .innerRadius(radius * 0.52).outerRadius(radius);

    g.selectAll('path').data(pie(pieData)).join('path')
      .attr('d', arc).attr('fill', d => d.data.color)
      .attr('stroke', '#1e293b').attr('stroke-width', 1.5);

    const total = pieData.reduce((s, d) => s + d.value, 0);
    g.append('text').attr('text-anchor', 'middle').attr('dy', '-0.1em')
      .text(fmtWon(total))
      .style('font-size', '14px').style('font-weight', '700').style('fill', '#e2e8f0');
    g.append('text').attr('text-anchor', 'middle').attr('dy', '1.2em')
      .text('원')
      .style('font-size', '9px').style('fill', '#64748b');

    const legendX = cx + radius + 24;
    pieData.forEach((d, i) => {
      const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0';
      const row = svg.append('g').attr('transform', `translate(${legendX},${cy - 30 + i * 24})`);
      row.append('rect').attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', d.color);
      row.append('text').attr('x', 14).attr('y', 10)
        .text(`${d.label}: ${fmtWon(d.value)}원 (${pct}%)`)
        .style('font-size', '10px').style('fill', '#cbd5e1');
    });
  }, [pieData, containerWidth]);

  return <div ref={ref} className="chart-container" style={{ minHeight: 180 }} />;
}
