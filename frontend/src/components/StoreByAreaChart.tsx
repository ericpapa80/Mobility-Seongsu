import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { Store, GeoJSONCollection } from '../api/client';
import type { StoreSettings } from './Sidebar';
import { extractAreas, findArea } from '../lib/geo';
import './ChartCommon.css';

interface Props {
  stores: Store[];
  commercialAreaGeoJson: GeoJSONCollection;
  storeSettings: StoreSettings;
}

const CAT_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};

export default function StoreByAreaChart({ stores, commercialAreaGeoJson, storeSettings }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const areas = useMemo(() => extractAreas(commercialAreaGeoJson), [commercialAreaGeoJson]);

  const grouped = useMemo(() => {
    const filtered = stores.filter(s => storeSettings.categories.includes(s.category_bg));
    const map = new Map<string, Record<string, number>>();

    for (const s of filtered) {
      const area = findArea(s.lng, s.lat, areas);
      if (!map.has(area)) map.set(area, {});
      const row = map.get(area)!;
      row[s.category_bg] = (row[s.category_bg] ?? 0) + 1;
    }

    return [...map.entries()]
      .map(([area, cats]) => ({
        area,
        ...cats,
        total: Object.values(cats).reduce((a, b) => a + b, 0),
      }))
      .sort((a, b) => b.total - a.total);
  }, [stores, areas, storeSettings.categories]);

  useEffect(() => {
    const el = ref.current;
    if (!el || grouped.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const barH = 22;
    const margin = { top: 8, right: 50, bottom: 20, left: 76 };
    const ih = grouped.length * barH;
    const height = ih + margin.top + margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
    const iw = width - margin.left - margin.right;

    const cats = storeSettings.categories;
    const stack = d3.stack<Record<string, unknown>>()
      .keys(cats)
      .value((d, key) => (d[key] as number) ?? 0)
      .order(d3.stackOrderNone)
      .offset(d3.stackOffsetNone);
    const series = stack(grouped as unknown as Record<string, unknown>[]);

    const y = d3.scaleBand()
      .domain(grouped.map(d => d.area))
      .range([0, ih])
      .padding(0.18);

    const xMax = d3.max(series, s => d3.max(s, d => d[1])) ?? 1;
    const x = d3.scaleLinear().domain([0, xMax]).nice().range([0, iw]);

    g.append('g')
      .call(d3.axisLeft(y).tickSize(0))
      .selectAll('text')
      .style('font-size', '10px')
      .style('fill', '#cbd5e1');

    g.selectAll('.domain').remove();

    series.forEach(s => {
      const cat = s.key;
      g.selectAll(`rect.bar-${cat}`)
        .data(s)
        .join('rect')
        .attr('y', (d) => y((d.data as { area: string }).area)!)
        .attr('x', d => x(d[0]))
        .attr('width', d => Math.max(0, x(d[1]) - x(d[0])))
        .attr('height', y.bandwidth())
        .attr('fill', CAT_COLORS[cat] ?? '#94a3b8')
        .attr('rx', 2)
        .attr('opacity', 0.85)
        .attr('data-cat', cat);
    });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect').style('cursor', 'pointer')
      .on('mouseenter', function(_e: MouseEvent, d: d3.SeriesPoint<Record<string, unknown>>) {
        const cat = d3.select(this).attr('data-cat') || '';
        const val = d[1] - d[0];
        tooltip.style('opacity', '1').html(`<b>${(d.data as { area: string }).area}</b><br/>${cat}: ${val}개`);
      })
      .on('mousemove', (event: MouseEvent) => {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    g.selectAll('text.total-label')
      .data(grouped)
      .join('text')
      .attr('class', 'total-label')
      .attr('x', d => x(d.total) + 4)
      .attr('y', d => y(d.area)! + y.bandwidth() / 2)
      .attr('dy', '0.35em')
      .text(d => d.total.toLocaleString())
      .style('font-size', '9px')
      .style('fill', '#94a3b8')
      .style('font-family', "'JetBrains Mono', monospace");

    const gLegend = svg.append('g')
      .attr('transform', `translate(${margin.left},${height - 14})`);
    cats.forEach((cat, i) => {
      const lg = gLegend.append('g').attr('transform', `translate(${i * 56},0)`);
      lg.append('rect').attr('width', 8).attr('height', 8).attr('rx', 1.5)
        .attr('fill', CAT_COLORS[cat] ?? '#94a3b8');
      lg.append('text').attr('x', 11).attr('y', 7)
        .text(cat)
        .style('font-size', '9px').style('fill', '#94a3b8');
    });
  }, [grouped, storeSettings.categories]);

  if (grouped.length === 0) return null;

  const dynamicH = grouped.length * 22 + 28;

  return <div ref={ref} className="chart-container" style={{ minHeight: Math.max(120, dynamicH) }} />;
}
