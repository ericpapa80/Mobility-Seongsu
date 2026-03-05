import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { Store, StoreTrend } from '../api/client';
import { fmtWon, fmtAxisWon } from '../lib/format';
import './StoreDetailPanel.css';

interface Props {
  store: Store;
  onClose: () => void;
}

function drawBarChart(
  el: HTMLDivElement,
  entries: [string, number][],
  color: string,
  height = 120,
) {
  const width = el.getBoundingClientRect().width || 320;
  const margin = { top: 8, right: 8, bottom: 24, left: 40 };
  const iw = width - margin.left - margin.right;
  const ih = height - margin.top - margin.bottom;

  d3.select(el).selectAll('*').remove();
  const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const x = d3.scaleBand().domain(entries.map(d => d[0])).range([0, iw]).padding(0.2);
  const y = d3.scaleLinear().domain([0, d3.max(entries, d => d[1]) ?? 1]).nice().range([ih, 0]);

  g.append('g').attr('transform', `translate(0,${ih})`).call(d3.axisBottom(x).tickSize(0))
    .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');
  g.append('g').call(d3.axisLeft(y).ticks(3).tickFormat(fmtAxisWon))
    .selectAll('text').style('font-size', '8px').style('fill', '#64748b');
  g.selectAll('.domain').remove();

  g.selectAll('rect').data(entries).join('rect')
    .attr('x', d => x(d[0])!)
    .attr('y', d => y(d[1])).attr('width', x.bandwidth()).attr('height', d => ih - y(d[1]))
    .attr('fill', color).attr('rx', 2).attr('opacity', 0.85);

  g.selectAll('.val-label').data(entries).join('text')
    .attr('class', 'val-label')
    .attr('x', d => (x(d[0]) ?? 0) + x.bandwidth() / 2)
    .attr('y', d => y(d[1]) - 3)
    .attr('text-anchor', 'middle')
    .text(d => d[1] > 0 ? fmtWon(d[1]) : '')
    .style('font-size', '8px').style('fill', '#94a3b8');
}

export default function StoreDetailPanel({ store, onClose }: Props) {
  const timeRef = useRef<HTMLDivElement>(null);
  const weekdayRef = useRef<HTMLDivElement>(null);
  const genderRef = useRef<HTMLDivElement>(null);
  const pecoRef = useRef<HTMLDivElement>(null);
  const famRef = useRef<HTMLDivElement>(null);
  const wdweRef = useRef<HTMLDivElement>(null);
  const revfreqRef = useRef<HTMLDivElement>(null);
  const trendRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (timeRef.current) drawBarChart(timeRef.current, Object.entries(store.times), '#fb923c');
    if (weekdayRef.current) drawBarChart(weekdayRef.current, Object.entries(store.weekday), '#3b82f6', 100);
    drawGenderChart();
    drawPecoChart();
    if (famRef.current) drawBarChart(famRef.current, Object.entries(store.fam), '#8b5cf6', 100);
    if (wdweRef.current && store.wdwe) drawBarChart(wdweRef.current, Object.entries(store.wdwe), '#06b6d4', 100);
    drawRevfreqChart();
    drawTrendChart();
  }, [store]);

  function drawGenderChart() {
    const el = genderRef.current;
    if (!el) return;
    const ages = ['20대', '30대', '40대', '50대', '60대'];
    const fVals = ages.map(a => store.gender_f[a] ?? 0);
    const mVals = ages.map(a => store.gender_m[a] ?? 0);

    const width = el.getBoundingClientRect().width || 320;
    const height = 120;
    const margin = { top: 8, right: 8, bottom: 24, left: 40 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const maxVal = d3.max([...fVals, ...mVals]) ?? 1;

    const x0 = d3.scaleBand().domain(ages).range([0, iw]).padding(0.2);
    const x1 = d3.scaleBand().domain(['여', '남']).range([0, x0.bandwidth()]).padding(0.05);
    const y = d3.scaleLinear().domain([0, maxVal]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`).call(d3.axisBottom(x0).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');
    g.append('g').call(d3.axisLeft(y).ticks(3).tickFormat(fmtAxisWon))
      .selectAll('text').style('font-size', '8px').style('fill', '#64748b');
    g.selectAll('.domain').remove();

    ages.forEach((age, i) => {
      const gg = g.append('g').attr('transform', `translate(${x0(age)},0)`);
      gg.append('rect')
        .attr('x', x1('여')!).attr('y', y(fVals[i])).attr('width', x1.bandwidth())
        .attr('height', ih - y(fVals[i])).attr('fill', '#ec4899').attr('rx', 1).attr('opacity', 0.8);
      gg.append('rect')
        .attr('x', x1('남')!).attr('y', y(mVals[i])).attr('width', x1.bandwidth())
        .attr('height', ih - y(mVals[i])).attr('fill', '#3b82f6').attr('rx', 1).attr('opacity', 0.8);
    });
  }

  function drawPecoChart() {
    const el = pecoRef.current;
    if (!el) return;
    const data = [
      { label: '개인', value: store.peco_individual, color: '#10b981' },
      { label: '법인', value: store.peco_corporate, color: '#3b82f6' },
      { label: '외국인', value: store.peco_foreign, color: '#f59e0b' },
    ].filter(d => d.value > 0);

    const width = el.getBoundingClientRect().width || 320;
    const height = 100;
    const radius = 38;
    const center = { x: width / 2, y: height / 2 };

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${center.x},${center.y})`);

    const pie = d3.pie<typeof data[0]>().value(d => d.value).sort(null);
    const arc = d3.arc<d3.PieArcDatum<typeof data[0]>>().innerRadius(radius * 0.5).outerRadius(radius);

    g.selectAll('path').data(pie(data)).join('path')
      .attr('d', arc).attr('fill', d => d.data.color).attr('stroke', '#0c0c0c').attr('stroke-width', 1.5);

    const total = data.reduce((s, d) => s + d.value, 0);
    g.append('text').attr('text-anchor', 'middle').attr('dy', '0.35em')
      .text(fmtWon(total) + '원')
      .style('font-size', '12px').style('font-weight', '700').style('fill', '#e2e8f0');

    const legendX = center.x + radius + 16 - center.x;
    data.forEach((d, i) => {
      const row = g.append('g').attr('transform', `translate(${legendX + 50},${-20 + i * 18})`);
      row.append('rect').attr('width', 8).attr('height', 8).attr('rx', 1).attr('fill', d.color);
      row.append('text').attr('x', 12).attr('y', 8)
        .text(`${d.label}: ${fmtWon(d.value)}원`)
        .style('font-size', '10px').style('fill', '#cbd5e1');
    });
  }

  function drawRevfreqChart() {
    const el = revfreqRef.current;
    if (!el) return;
    const data: [string, number][] = [
      ['평일', store.revfreq_weekday],
      ['공휴일', store.revfreq_holiday],
    ];

    const width = el.getBoundingClientRect().width || 320;
    const height = 90;
    const margin = { top: 8, right: 8, bottom: 24, left: 40 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleBand().domain(data.map(d => d[0])).range([0, iw]).padding(0.35);
    const y = d3.scaleLinear().domain([0, d3.max(data, d => d[1]) ?? 1]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`).call(d3.axisBottom(x).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');
    g.append('g').call(d3.axisLeft(y).ticks(3))
      .selectAll('text').style('font-size', '8px').style('fill', '#64748b');
    g.selectAll('.domain').remove();

    g.selectAll('rect').data(data).join('rect')
      .attr('x', d => x(d[0])!)
      .attr('y', d => y(d[1])).attr('width', x.bandwidth()).attr('height', d => ih - y(d[1]))
      .attr('fill', '#f59e0b').attr('rx', 2).attr('opacity', 0.85);

    g.selectAll('.val-label').data(data).join('text')
      .attr('class', 'val-label')
      .attr('x', d => (x(d[0]) ?? 0) + x.bandwidth() / 2)
      .attr('y', d => y(d[1]) - 3)
      .attr('text-anchor', 'middle')
      .text(d => d[1] > 0 ? d[1].toFixed(1) : '')
      .style('font-size', '9px').style('font-weight', '600').style('fill', '#f59e0b');
  }

  function drawTrendChart() {
    const el = trendRef.current;
    if (!el || !store.trend || store.trend.length === 0) return;
    const data: StoreTrend[] = store.trend;

    const width = el.getBoundingClientRect().width || 320;
    const height = 140;
    const margin = { top: 12, right: 44, bottom: 24, left: 44 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear()
      .domain(d3.extent(data, d => d.year) as [number, number])
      .range([0, iw]);
    const yStore = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.store) ?? 1]).nice()
      .range([ih, 0]);
    const yCnt = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.cnt) ?? 1]).nice()
      .range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).ticks(data.length).tickFormat(d => String(d)))
      .selectAll('text').style('font-size', '8px').style('fill', '#94a3b8');
    g.append('g')
      .call(d3.axisLeft(yStore).ticks(4).tickFormat(fmtAxisWon))
      .selectAll('text').style('font-size', '8px').style('fill', '#10b981');
    g.append('g').attr('transform', `translate(${iw},0)`)
      .call(d3.axisRight(yCnt).ticks(4).tickFormat(d3.format('~s')))
      .selectAll('text').style('font-size', '8px').style('fill', '#f59e0b');
    g.selectAll('.domain').remove();

    const lineStore = d3.line<StoreTrend>().x(d => x(d.year)).y(d => yStore(d.store)).curve(d3.curveMonotoneX);
    const lineCnt = d3.line<StoreTrend>().x(d => x(d.year)).y(d => yCnt(d.cnt)).curve(d3.curveMonotoneX);

    g.append('path').datum(data).attr('d', lineStore)
      .attr('fill', 'none').attr('stroke', '#10b981').attr('stroke-width', 2).attr('opacity', 0.9);
    g.selectAll('.dot-store').data(data).join('circle')
      .attr('cx', d => x(d.year)).attr('cy', d => yStore(d.store))
      .attr('r', 3).attr('fill', '#10b981');

    g.append('path').datum(data).attr('d', lineCnt)
      .attr('fill', 'none').attr('stroke', '#f59e0b').attr('stroke-width', 2)
      .attr('stroke-dasharray', '4,2').attr('opacity', 0.9);
    g.selectAll('.dot-cnt').data(data).join('circle')
      .attr('cx', d => x(d.year)).attr('cy', d => yCnt(d.cnt))
      .attr('r', 3).attr('fill', '#f59e0b');

    const legend = svg.append('g').attr('transform', `translate(${margin.left + 4},${margin.top - 2})`);
    legend.append('line').attr('x1', 0).attr('x2', 14).attr('y1', 0).attr('y2', 0)
      .attr('stroke', '#10b981').attr('stroke-width', 2);
    legend.append('text').attr('x', 18).attr('y', 3)
      .text('매출').style('font-size', '8px').style('fill', '#10b981');
    legend.append('line').attr('x1', 80).attr('x2', 94).attr('y1', 0).attr('y2', 0)
      .attr('stroke', '#f59e0b').attr('stroke-width', 2).attr('stroke-dasharray', '4,2');
    legend.append('text').attr('x', 98).attr('y', 3)
      .text('건수(건)').style('font-size', '8px').style('fill', '#f59e0b');
  }

  return (
    <div className="store-detail-panel">
      <div className="store-detail-header">
        <h3>{store.name || '상가 상세'}</h3>
        <button className="store-detail-close" onClick={onClose}>
          <i className="ri-close-line" />
        </button>
      </div>

      <div className="store-detail-body">
        <div className="store-meta">
          <div className="store-meta-row">
            <i className="ri-store-2-line" />
            <span className="label">업종</span>
            <span className="value">{store.category_bg} &gt; {store.category_mi} &gt; {store.category_sl}</span>
          </div>
          <div className="store-meta-row">
            <i className="ri-map-pin-line" />
            <span className="label">주소</span>
            <span className="value">{store.road_address}</span>
          </div>
        </div>

        <div className="store-stat-grid">
          <div className="store-stat-card">
            <div className="store-stat-value">{fmtWon(store.peco_individual)}원</div>
            <div className="store-stat-label">개인 매출</div>
          </div>
          <div className="store-stat-card">
            <div className="store-stat-value">{fmtWon(store.peco_corporate)}원</div>
            <div className="store-stat-label">법인 매출</div>
          </div>
          <div className="store-stat-card">
            <div className="store-stat-value">{fmtWon(store.peco_foreign)}원</div>
            <div className="store-stat-label">외국인 매출</div>
          </div>
        </div>

        <div className="store-section-title">시간대별 매출 패턴</div>
        <div ref={timeRef} className="store-chart-container" />

        <div className="store-section-title">요일별 매출</div>
        <div ref={weekdayRef} className="store-chart-container" />

        <div className="store-section-title">성별/연령별 매출</div>
        <div ref={genderRef} className="store-chart-container" />

        <div className="store-section-title">소비자 유형별 매출 비율</div>
        <div ref={pecoRef} className="store-chart-container" />

        <div className="store-section-title">세대별 매출</div>
        <div ref={famRef} className="store-chart-container" />

        <div className="store-section-title">평일/공휴일 매출</div>
        <div ref={wdweRef} className="store-chart-container" />

        <div className="store-section-title">재방문 빈도 (평균)</div>
        <div ref={revfreqRef} className="store-chart-container" />

        {store.trend && store.trend.length > 0 && (
          <>
            <div className="store-section-title">연도별 매출 추이 (2018~2025)</div>
            <div ref={trendRef} className="store-chart-container" />
          </>
        )}
      </div>
    </div>
  );
}
