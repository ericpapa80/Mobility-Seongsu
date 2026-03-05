import { useRef, useEffect, useMemo } from 'react';
import * as d3 from 'd3';
import type { BusStopHourlyFull, GeoJSONCollection } from '../api/client';
import { extractAreas, findArea } from '../lib/geo';
import './ChartCommon.css';

interface Props {
  stops: BusStopHourlyFull[];
  commercialAreaGeoJson: GeoJSONCollection;
}

const RIDE_COLOR = '#3b82f6';
const ALIGHT_COLOR = '#ef4444';

export default function AreaBusChart({ stops, commercialAreaGeoJson }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  const areas = useMemo(
    () => extractAreas(commercialAreaGeoJson),
    [commercialAreaGeoJson],
  );

  const grouped = useMemo(() => {
    const map = new Map<string, { ride: number; alight: number }>();

    for (const stop of stops) {
      const areaName = findArea(stop.lng, stop.lat, areas);
      const row = map.get(areaName) ?? { ride: 0, alight: 0 };
      row.ride += stop.total_ride;
      row.alight += stop.total_alight;
      map.set(areaName, row);
    }

    return [...map.entries()]
      .map(([area, { ride, alight }]) => ({
        area,
        ride,
        alight,
        total: ride + alight,
      }))
      .sort((a, b) => b.total - a.total);
  }, [stops, areas]);

  useEffect(() => {
    const el = ref.current;
    if (!el || grouped.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 220;
    const barH = 22;
    const margin = { top: 8, right: 60, bottom: 36, left: 76 };
    const ih = Math.min(grouped.length * barH, height - margin.top - margin.bottom);

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
    const iw = width - margin.left - margin.right;

    const y = d3
      .scaleBand()
      .domain(grouped.map((d) => d.area))
      .range([0, ih])
      .padding(0.18);

    const xMax = d3.max(grouped, (d) => d.total) ?? 1;
    const x = d3.scaleLinear().domain([0, xMax]).range([0, iw]);

    g.append('g')
      .call(d3.axisLeft(y).tickSize(0))
      .selectAll('text')
      .style('font-size', '10px')
      .style('fill', '#cbd5e1');

    g.selectAll('.domain').remove();

    g.selectAll('rect.ride')
      .data(grouped)
      .join('rect')
      .attr('class', 'ride')
      .attr('y', (d) => y(d.area)!)
      .attr('x', 0)
      .attr('width', (d) => x(d.ride))
      .attr('height', y.bandwidth())
      .attr('fill', RIDE_COLOR)
      .attr('rx', 2);

    g.selectAll('rect.alight')
      .data(grouped)
      .join('rect')
      .attr('class', 'alight')
      .attr('y', (d) => y(d.area)!)
      .attr('x', (d) => x(d.ride))
      .attr('width', (d) => x(d.total) - x(d.ride))
      .attr('height', y.bandwidth())
      .attr('fill', ALIGHT_COLOR)
      .attr('rx', 2);

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');

    const showTooltip = (event: MouseEvent, d: (typeof grouped)[0]) => {
      tooltip
        .style('opacity', '1')
        .html(
          `<b>${d.area}</b><br/>승차: ${d.ride.toLocaleString()}명 / 하차: ${d.alight.toLocaleString()}명<br/>합계: ${d.total.toLocaleString()}명`,
        );
      const [mx, my] = d3.pointer(event, el);
      tooltip.style('left', mx + 12 + 'px').style('top', my - 10 + 'px');
    };

    const hoverLayer = g.append('g').attr('class', 'hover-layer');
    hoverLayer
      .selectAll('rect.hover-rect')
      .data(grouped)
      .join('rect')
      .attr('class', 'hover-rect')
      .attr('fill', 'transparent')
      .attr('y', (d) => y(d.area)!)
      .attr('x', 0)
      .attr('width', iw)
      .attr('height', y.bandwidth())
      .style('cursor', 'pointer')
      .on('mouseenter', function (e: MouseEvent, d) {
        showTooltip(e, d);
      })
      .on('mousemove', (e: MouseEvent) => {
        const [mx, my] = d3.pointer(e, el);
        tooltip.style('left', mx + 12 + 'px').style('top', my - 10 + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    const gLegend = svg.append('g').attr('transform', `translate(${margin.left},${height - 20})`);
    gLegend
      .append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', 10)
      .attr('height', 8)
      .attr('fill', RIDE_COLOR)
      .attr('rx', 1);
    gLegend
      .append('text')
      .attr('x', 14)
      .attr('y', 7)
      .text('승차')
      .style('font-size', '9px')
      .style('fill', '#94a3b8');
    gLegend
      .append('rect')
      .attr('x', 52)
      .attr('y', 0)
      .attr('width', 10)
      .attr('height', 8)
      .attr('fill', ALIGHT_COLOR)
      .attr('rx', 1);
    gLegend
      .append('text')
      .attr('x', 66)
      .attr('y', 7)
      .text('하차')
      .style('font-size', '9px')
      .style('fill', '#94a3b8');
  }, [grouped]);

  if (grouped.length === 0) return null;

  return (
    <div ref={ref} className="chart-container d3-chart" style={{ height: 220 }} />
  );
}
