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

interface AreaSales {
  area: string;
  total: number;
  count: number;
}

export default function AreaSalesChart({ stores, commercialAreaGeoJson, storeSettings }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const areas = useMemo(() => extractAreas(commercialAreaGeoJson), [commercialAreaGeoJson]);

  const grouped = useMemo(() => {
    const filtered = stores.filter(s => storeSettings.categories.includes(s.category_bg));
    const map = new Map<string, { total: number; count: number }>();

    for (const s of filtered) {
      const area = findArea(s.lng, s.lat, areas);
      const entry = map.get(area) ?? { total: 0, count: 0 };
      entry.total += s.peco_total;
      entry.count += 1;
      map.set(area, entry);
    }

    return [...map.entries()]
      .map(([area, { total, count }]) => ({ area, total, count }))
      .sort((a, b) => b.total - a.total);
  }, [stores, areas, storeSettings.categories]);

  useEffect(() => {
    const el = ref.current;
    if (!el || grouped.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 220;
    const barH = Math.max(18, (height - 40) / grouped.length - 4);
    const ih = grouped.length * barH;
    const margin = { top: 8, right: 50, bottom: 28, left: 80 };
    const chartHeight = Math.min(height, ih + margin.top + margin.bottom);
    const iw = width - margin.left - margin.right;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', chartHeight);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const y = d3.scaleBand()
      .domain(grouped.map(d => d.area))
      .range([0, ih])
      .padding(0.18);

    const xMax = d3.max(grouped, d => d.total) ?? 1;
    const x = d3.scaleLinear().domain([0, xMax]).nice().range([0, iw]);

    g.append('g')
      .call(d3.axisLeft(y).tickSize(0))
      .selectAll('text')
      .style('font-size', '10px')
      .style('fill', '#cbd5e1');

    g.append('g')
      .attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d => d + '만'))
      .selectAll('text')
      .style('font-size', '9px')
      .style('fill', '#94a3b8');

    g.selectAll('.domain').remove();

    g.selectAll('rect.bar')
      .data(grouped)
      .join('rect')
      .attr('class', 'bar')
      .attr('y', d => y(d.area)!)
      .attr('x', 0)
      .attr('width', d => x(d.total))
      .attr('height', y.bandwidth())
      .attr('fill', '#fb923c')
      .attr('rx', 2)
      .attr('opacity', 0.85);

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect.bar')
      .style('cursor', 'pointer')
      .on('mouseenter', (_e: MouseEvent, d: AreaSales) => {
        tooltip
          .style('opacity', '1')
          .html(`<b>${d.area}</b><br/>매출: ${d.total.toLocaleString()}만원<br/>점포: ${d.count.toLocaleString()}개`);
      })
      .on('mousemove', (event: MouseEvent) => {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));
  }, [grouped]);

  if (grouped.length === 0) return null;

  const dynamicH = grouped.length * 22 + 36;

  return (
    <div
      ref={ref}
      className="chart-container"
      style={{ minHeight: Math.max(140, Math.min(220, dynamicH)) }}
    />
  );
}
