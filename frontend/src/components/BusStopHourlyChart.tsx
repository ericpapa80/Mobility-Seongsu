import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { BusStopHourlyFull } from '../api/client';
import { useResizeKey } from '../hooks/useResizeKey';
import './ChartCommon.css';

interface Props {
  stops: BusStopHourlyFull[];
  mode: 'ride' | 'alight' | 'total';
  currentHour: number;
}

export default function BusStopHourlyChart({ stops, mode, currentHour }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const resizeKey = useResizeKey(ref);

  useEffect(() => {
    const el = ref.current;
    if (!el || stops.length === 0) return;

    const rect = el.getBoundingClientRect();
    const width = rect.width || 320;
    const height = 200;
    const margin = { top: 12, right: 12, bottom: 28, left: 40 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const top10 = [...stops]
      .sort((a, b) => b.total - a.total)
      .slice(0, 10);

    if (top10.length === 0) {
      g.append('text').attr('x', iw / 2).attr('y', ih / 2)
        .attr('text-anchor', 'middle').text('승하차 데이터 없음')
        .style('fill', '#64748b').style('font-size', '12px');
      return;
    }

    const rideAgg = Array.from({ length: 24 }, (_, h) =>
      top10.reduce((sum, s) => sum + (s.hourly.ride[h] ?? 0), 0));
    const alightAgg = Array.from({ length: 24 }, (_, h) =>
      top10.reduce((sum, s) => sum + (s.hourly.alight[h] ?? 0), 0));
    const totalAgg = rideAgg.map((r, i) => r + alightAgg[i]);

    const displayData = mode === 'ride' ? rideAgg : mode === 'alight' ? alightAgg : totalAgg;
    const chartColor = mode === 'ride' ? '#06b6d4' : mode === 'alight' ? '#ec4899' : '#3b82f6';

    const x = d3.scaleLinear().domain([0, 23]).range([0, iw]);
    const yMax = d3.max(displayData) ?? 1;
    const y = d3.scaleLinear().domain([0, yMax * 1.1]).range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(8).tickFormat(d => `${d}시`))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d3.format(',.0f')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    const area = d3.area<number>()
      .x((_, i) => x(i)).y0(ih).y1(d => y(d))
      .curve(d3.curveMonotoneX);

    const line = d3.line<number>()
      .x((_, i) => x(i)).y(d => y(d))
      .curve(d3.curveMonotoneX);

    g.append('path').datum(displayData)
      .attr('fill', `${chartColor}25`)
      .attr('d', area);

    g.append('path').datum(displayData)
      .attr('fill', 'none')
      .attr('stroke', chartColor)
      .attr('stroke-width', 2)
      .attr('d', line);

    if (mode === 'total') {
      const areaRide = d3.area<number>()
        .x((_, i) => x(i)).y0(ih).y1(d => y(d))
        .curve(d3.curveMonotoneX);
      const areaAlight = d3.area<number>()
        .x((_, i) => x(i)).y0(ih).y1(d => y(d))
        .curve(d3.curveMonotoneX);
      g.append('path').datum(rideAgg)
        .attr('fill', '#06b6d415')
        .attr('d', areaRide);
      g.append('path').datum(rideAgg)
        .attr('fill', 'none').attr('stroke', '#06b6d4')
        .attr('stroke-width', 1).attr('stroke-dasharray', '4,2')
        .attr('d', d3.line<number>().x((_, i) => x(i)).y(d => y(d)).curve(d3.curveMonotoneX));
      g.append('path').datum(alightAgg)
        .attr('fill', '#ec489915')
        .attr('d', areaAlight);
      g.append('path').datum(alightAgg)
        .attr('fill', 'none').attr('stroke', '#ec4899')
        .attr('stroke-width', 1).attr('stroke-dasharray', '2,4')
        .attr('d', d3.line<number>().x((_, i) => x(i)).y(d => y(d)).curve(d3.curveMonotoneX));
    }

    g.append('line')
      .attr('x1', x(currentHour)).attr('x2', x(currentHour))
      .attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#f59e0b').attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4,3').attr('opacity', 0.7);

    g.selectAll('circle')
      .data(displayData.filter((_, i) => i % 2 === 0))
      .join('circle')
      .attr('cx', (_, i) => x(i * 2))
      .attr('cy', d => y(d))
      .attr('r', 3)
      .attr('fill', chartColor)
      .attr('stroke', '#0a0e1a')
      .attr('stroke-width', 1.5);

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    const guideLine = g.append('line').attr('y1', 0).attr('y2', ih)
      .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '3,2').style('display', 'none');
    const hoverDot = g.append('circle').attr('r', 3.5)
      .attr('fill', '#f59e0b').attr('stroke', '#0a0e1a').attr('stroke-width', 1.5).style('display', 'none');

    g.append('rect').attr('width', iw).attr('height', ih).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('mousemove', (event: MouseEvent) => {
        const [mx] = d3.pointer(event);
        const h = Math.max(0, Math.min(23, Math.round(x.invert(mx))));
        guideLine.attr('x1', x(h)).attr('x2', x(h)).style('display', null);
        hoverDot.attr('cx', x(h)).attr('cy', y(displayData[h])).style('display', null);
        const modeLabel = mode === 'ride' ? '승차' : mode === 'alight' ? '하차' : '합계';
        let html = `<b>${h}시</b><br/>${modeLabel}: ${displayData[h].toLocaleString()}명`;
        if (mode === 'total') html += `<br/>승차: ${rideAgg[h].toLocaleString()}명 / 하차: ${alightAgg[h].toLocaleString()}명`;
        tooltip.style('opacity', '1').html(html);
        const [px, py] = d3.pointer(event, el);
        tooltip.style('left', (px + 12) + 'px').style('top', (py - 10) + 'px');
      })
      .on('mouseleave', () => {
        guideLine.style('display', 'none');
        hoverDot.style('display', 'none');
        tooltip.style('opacity', '0');
      });

    const legend = svg.append('g').attr('transform', `translate(${width - 200}, 4)`);
    if (mode === 'total') {
      legend.append('rect').attr('x', 0).attr('y', 0).attr('width', 10).attr('height', 3).attr('fill', '#3b82f6');
      legend.append('text').attr('x', 14).attr('y', 6).text('합계').style('font-size', '9px').style('fill', '#94a3b8');
      legend.append('rect').attr('x', 42).attr('y', 0).attr('width', 10).attr('height', 3).attr('fill', '#06b6d4');
      legend.append('text').attr('x', 56).attr('y', 6).text('승차').style('font-size', '9px').style('fill', '#94a3b8');
      legend.append('rect').attr('x', 90).attr('y', 0).attr('width', 10).attr('height', 3).attr('fill', '#ec4899');
      legend.append('text').attr('x', 104).attr('y', 6).text('하차').style('font-size', '9px').style('fill', '#94a3b8');
    }
  }, [stops, mode, currentHour, resizeKey]);

  return <div ref={ref} className="chart-container" />;
}
