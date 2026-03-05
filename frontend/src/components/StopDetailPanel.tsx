import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import { useBusStopDetail } from '../hooks/useMapData';
import './StopDetailPanel.css';

interface Props {
  stopId: number;
  stopName: string;
  onClose: () => void;
}

export default function StopDetailPanel({ stopId, stopName, onClose }: Props) {
  const { data, isLoading } = useBusStopDetail(stopId);
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!data?.hourly || !chartRef.current) return;

    const el = chartRef.current;
    const width = el.getBoundingClientRect().width || 320;
    const height = 180;
    const margin = { top: 12, right: 12, bottom: 28, left: 40 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const rideData = data.hourly.map(h => h.ride);
    const alightData = data.hourly.map(h => h.alight);
    const maxVal = d3.max([...rideData, ...alightData]) ?? 1;

    const x = d3.scaleLinear().domain([0, 23]).range([0, iw]);
    const y = d3.scaleLinear().domain([0, maxVal * 1.1]).range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(8).tickFormat(d => `${d}시`))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');
    g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(d3.format(',.0f')))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');
    g.selectAll('.domain').remove();

    const line = d3.line<number>().x((_, i) => x(i)).y(d => y(d)).curve(d3.curveMonotoneX);

    g.append('path').datum(rideData)
      .attr('fill', 'none').attr('stroke', '#06b6d4').attr('stroke-width', 2).attr('d', line);
    g.append('path').datum(alightData)
      .attr('fill', 'none').attr('stroke', '#ec4899').attr('stroke-width', 2).attr('d', line);

    const legendG = g.append('g').attr('transform', `translate(${iw - 100}, 0)`);
    [{ label: '승차', color: '#06b6d4' }, { label: '하차', color: '#ec4899' }].forEach((item, i) => {
      const lg = legendG.append('g').attr('transform', `translate(${i * 50}, 0)`);
      lg.append('line').attr('x1', 0).attr('x2', 12).attr('y1', 4).attr('y2', 4)
        .attr('stroke', item.color).attr('stroke-width', 2);
      lg.append('text').attr('x', 16).attr('y', 8)
        .text(item.label).style('font-size', '9px').style('fill', '#94a3b8');
    });
  }, [data]);

  return (
    <div className="stop-detail-panel">
      <div className="stop-detail-header">
        <h3>{stopName}</h3>
        <button className="close-btn" onClick={onClose}><i className="ri-close-line" /></button>
      </div>
      {isLoading && <div className="loading">로딩 중…</div>}
      {data && (
        <>
          <div className="stop-info-row">
            <span>ARS: {data.ars_id}</span>
            <span>노선: {data.routes?.join(', ')}</span>
          </div>
          <div className="chart-label">시간대별 승하차 추이</div>
          <div ref={chartRef} className="chart-container" />
        </>
      )}
    </div>
  );
}
