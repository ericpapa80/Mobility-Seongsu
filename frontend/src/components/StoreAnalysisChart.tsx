import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { Store } from '../api/client';
import type { StoreSettings } from './Sidebar';
import './ChartCommon.css';

interface Props {
  stores: Store[];
  settings: StoreSettings;
}

const CATEGORY_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};

export default function StoreAnalysisChart({ stores, settings }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const byCategory = useMemo(() => {
    const filtered = stores.filter(s => settings.categories.includes(s.category_bg));
    const map = new Map<string, number>();
    for (const s of filtered) {
      map.set(s.category_bg, (map.get(s.category_bg) ?? 0) + s.peco_total);
    }
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }, [stores, settings.categories]);

  useEffect(() => {
    const el = ref.current;
    if (!el || byCategory.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const donutRadius = 78;
    const margin = { top: 28, right: 8, bottom: 0, left: 4 };
    const height = margin.top + donutRadius * 2 + margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);

    const donutCenter = { x: donutRadius + margin.left + 4, y: margin.top + donutRadius };
    const gDonut = svg.append('g').attr('transform', `translate(${donutCenter.x},${donutCenter.y})`);

    const pie = d3.pie<[string, number]>().value(d => d[1]).sort(null);
    const arc = d3.arc<d3.PieArcDatum<[string, number]>>()
      .innerRadius(donutRadius * 0.55)
      .outerRadius(donutRadius);

    gDonut.selectAll('path')
      .data(pie(byCategory))
      .join('path')
      .attr('d', arc)
      .attr('fill', d => CATEGORY_COLORS[d.data[0]] ?? '#64748b')
      .attr('stroke', '#0c0c0c')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer');

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');

    gDonut.selectAll('path')
      .on('mouseenter', (_e: MouseEvent, d: d3.PieArcDatum<[string, number]>) => {
        tooltip.style('opacity', '1').html(`${d.data[0]}: ${d.data[1].toLocaleString()}만원`);
      })
      .on('mousemove', (event: MouseEvent) => {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    const total = byCategory.reduce((s, [, v]) => s + v, 0);
    gDonut.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '-0.2em')
      .text(total.toLocaleString())
      .style('font-size', '18px')
      .style('font-weight', '700')
      .style('fill', '#e2e8f0');

    gDonut.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '1.2em')
      .text('만원')
      .style('font-size', '11px')
      .style('fill', '#94a3b8');

    const legendX = donutCenter.x + donutRadius + 24;
    const legendWidth = width - legendX - margin.right;
    const legendY = donutCenter.y - (byCategory.length * 18) / 2 + 9;
    const gLegend = svg.append('g').attr('transform', `translate(${legendX},${legendY})`);
    byCategory.forEach(([cat, cnt], i) => {
      const row = gLegend.append('g').attr('transform', `translate(0,${i * 18})`);
      row.append('rect').attr('width', 10).attr('height', 10).attr('rx', 2)
        .attr('fill', CATEGORY_COLORS[cat] ?? '#64748b');
      row.append('text').attr('x', 16).attr('y', 9).attr('text-anchor', 'start')
        .text(cat)
        .style('font-size', '11px').style('fill', '#cbd5e1');
      row.append('text').attr('x', legendWidth).attr('y', 9).attr('text-anchor', 'end')
        .text(cnt.toLocaleString())
        .style('font-size', '11px').style('fill', '#cbd5e1')
        .style('font-family', "'JetBrains Mono', monospace")
        .style('font-variant-numeric', 'tabular-nums');
    });
  }, [byCategory]);

  if (byCategory.length === 0) return null;

  return <div ref={ref} className="chart-container" style={{ minHeight: 184 }} />;
}
