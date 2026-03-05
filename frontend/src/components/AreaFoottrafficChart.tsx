import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { FoottrafficLink, GeoJSONCollection } from '../api/client';
import type { FoottrafficSettings } from './Sidebar';
import { extractAreas, findArea } from '../lib/geo';
import './ChartCommon.css';

interface Props {
  links: FoottrafficLink[];
  commercialAreaGeoJson: GeoJSONCollection;
  settings: FoottrafficSettings;
}

interface AreaTotal {
  area: string;
  acost: number;
  linkCount: number;
}

export default function AreaFoottrafficChart({
  links,
  commercialAreaGeoJson,
  settings,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const { dayweek, agrde } = settings;

  const areas = useMemo(
    () => extractAreas(commercialAreaGeoJson),
    [commercialAreaGeoJson],
  );

  const areaData = useMemo(() => {
    const map = new Map<string, { acost: number; linkCount: number }>();

    for (const link of links) {
      const areaName = findArea(link.centroid[0], link.centroid[1], areas);
      const slice = link.data?.[dayweek]?.[agrde];
      let linkAcost = 0;
      if (slice && typeof slice === 'object') {
        for (const key of Object.keys(slice)) {
          linkAcost += slice[key]?.acost ?? 0;
        }
      }

      const existing = map.get(areaName);
      if (existing) {
        existing.acost += linkAcost;
        existing.linkCount += 1;
      } else {
        map.set(areaName, { acost: linkAcost, linkCount: 1 });
      }
    }

    return [...map.entries()]
      .map(([area, { acost, linkCount }]) => ({ area, acost, linkCount }))
      .sort((a, b) => b.acost - a.acost);
  }, [links, areas, dayweek, agrde]);

  useEffect(() => {
    const el = ref.current;
    if (!el || areaData.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 340;
    const height = 220;
    const margin = { top: 8, right: 60, bottom: 20, left: 80 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const y = d3
      .scaleBand()
      .domain(areaData.map(d => d.area))
      .range([0, ih])
      .padding(0.2);

    const xMax = d3.max(areaData, d => d.acost) ?? 1;
    const x = d3.scaleLinear().domain([0, xMax]).nice().range([0, iw]);

    g.append('g')
      .call(d3.axisLeft(y).tickSize(0))
      .selectAll('text')
      .style('font-size', '10px')
      .style('fill', '#94a3b8');

    g.append('g')
      .attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(5).tickFormat(d3.format('~s')))
      .selectAll('text')
      .style('font-size', '9px')
      .style('fill', '#64748b');

    g.selectAll('.domain').remove();

    g.selectAll('rect.bar')
      .data(areaData)
      .join('rect')
      .attr('class', 'bar')
      .attr('x', 0)
      .attr('y', d => y(d.area)!)
      .attr('width', d => x(d.acost))
      .attr('height', y.bandwidth())
      .attr('fill', '#f59e0b')
      .attr('rx', 2);

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect.bar')
      .style('cursor', 'pointer')
      .on('mouseenter', (_e: MouseEvent, d: AreaTotal) => {
        tooltip
          .style('opacity', '1')
          .html(
            `<b>${d.area}</b><br/>통행량: ${d.acost.toLocaleString()}<br/>구간 수: ${d.linkCount.toLocaleString()}개`,
          );
      })
      .on('mousemove', (e: MouseEvent) => {
        const [mx, my] = d3.pointer(e, el);
        tooltip.style('left', mx + 12 + 'px').style('top', my - 10 + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));
  }, [areaData]);

  if (areaData.length === 0) return null;

  return (
    <div
      ref={ref}
      className="chart-container d3-chart"
      style={{ minHeight: 220, height: 220 }}
    />
  );
}
