import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import type { Store } from '../api/client';
import type { StoreSettings } from './Sidebar';
import { fmtWon, fmtAxisWon } from '../lib/format';
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
  currentHour: number;
}

const TIME_SLOTS = ['아침', '점심', '오후', '저녁', '밤', '심야', '새벽'];
const HOUR_TO_SLOT: Record<number, string> = {};
[6, 7, 8].forEach(h => HOUR_TO_SLOT[h] = '아침');
[9, 10, 11, 12, 13].forEach(h => HOUR_TO_SLOT[h] = '점심');
[14, 15, 16].forEach(h => HOUR_TO_SLOT[h] = '오후');
[17, 18, 19, 20].forEach(h => HOUR_TO_SLOT[h] = '저녁');
[21, 22, 23].forEach(h => HOUR_TO_SLOT[h] = '밤');
[0, 1, 2].forEach(h => HOUR_TO_SLOT[h] = '심야');
[3, 4, 5].forEach(h => HOUR_TO_SLOT[h] = '새벽');

const CAT_COLORS: Record<string, string> = {
  '음식': '#fb923c',
  '소매': '#3b82f6',
  '서비스': '#f472b6',
};

export default function StoreTimeFlowChart({ stores, settings, currentHour }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const containerWidth = useContainerWidth(ref);

  const filtered = useMemo(
    () => stores.filter(s => settings.categories.includes(s.category_bg)),
    [stores, settings.categories],
  );

  const stacked = useMemo(() => {
    const cats = settings.categories;
    return TIME_SLOTS.map(slot => {
      const row: Record<string, number> & { slot: string } = { slot } as never;
      for (const cat of cats) {
        let sum = 0;
        for (const s of filtered) {
          if (s.category_bg === cat) sum += s.times[slot] ?? 0;
        }
        row[cat] = sum;
      }
      return row;
    });
  }, [filtered, settings.categories]);

  useEffect(() => {
    const el = ref.current;
    if (!el || stacked.length === 0) return;

    const width = containerWidth || el.getBoundingClientRect().width || 340;
    const height = 210;
    const margin = { top: 22, right: 12, bottom: 28, left: 52 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const cats = settings.categories;
    const stack = d3.stack<Record<string, number> & { slot: string }>()
      .keys(cats)
      .order(d3.stackOrderNone)
      .offset(d3.stackOffsetNone);
    const series = stack(stacked);

    const x = d3.scaleBand().domain(TIME_SLOTS).range([0, iw]).padding(0.2);
    const yMax = d3.max(series, s => d3.max(s, d => d[1])) ?? 1;
    const y = d3.scaleLinear().domain([0, yMax]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(fmtAxisWon))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    const currentSlot = HOUR_TO_SLOT[currentHour] ?? '아침';

    series.forEach(s => {
      const cat = s.key;
      g.selectAll(`rect.bar-${cat}`)
        .data(s)
        .join('rect')
        .attr('x', d => x(d.data.slot)!)
        .attr('y', d => y(d[1]))
        .attr('width', x.bandwidth())
        .attr('height', d => y(d[0]) - y(d[1]))
        .attr('fill', CAT_COLORS[cat] ?? '#94a3b8')
        .attr('opacity', d => d.data.slot === currentSlot ? 1 : 0.6)
        .attr('rx', 2)
        .attr('data-cat', cat);
    });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('rect').style('cursor', 'pointer')
      .on('mouseenter', function(_e: MouseEvent, d: d3.SeriesPoint<Record<string, number> & { slot: string }>) {
        const cat = d3.select(this).attr('data-cat') || '';
        const val = d[1] - d[0];
        tooltip.style('opacity', '1').html(`<b>${d.data.slot}</b><br/>${cat}: ${fmtWon(val)}원`);
      })
      .on('mousemove', (event: MouseEvent) => {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    if (x(currentSlot) !== undefined) {
      g.append('line')
        .attr('x1', x(currentSlot)! + x.bandwidth() / 2)
        .attr('x2', x(currentSlot)! + x.bandwidth() / 2)
        .attr('y1', 0).attr('y2', ih)
        .attr('stroke', '#f59e0b').attr('stroke-width', 1.5).attr('stroke-dasharray', '4,3');
    }

    const legendItems = cats.map(c => ({ label: c, color: CAT_COLORS[c] ?? '#94a3b8' }));
    const legend = svg.append('g').attr('transform', `translate(${margin.left + iw - legendItems.length * 50},2)`);
    legendItems.forEach((item, i) => {
      legend.append('rect').attr('x', i * 50).attr('y', 0).attr('width', 8).attr('height', 8)
        .attr('fill', item.color).attr('rx', 2);
      legend.append('text').attr('x', i * 50 + 11).attr('y', 8)
        .text(item.label).style('font-size', '9px').style('fill', '#94a3b8');
    });
  }, [stacked, settings.categories, currentHour, containerWidth]);

  return <div ref={ref} className="chart-container" style={{ minHeight: 210 }} />;
}
