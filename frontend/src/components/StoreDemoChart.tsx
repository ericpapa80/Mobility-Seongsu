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
}

const AGE_GROUPS = ['20대', '30대', '40대', '50대', '60대'];

export default function StoreDemoChart({ stores, settings }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const containerWidth = useContainerWidth(ref);

  const filtered = useMemo(
    () => stores.filter(s => settings.categories.includes(s.category_bg)),
    [stores, settings.categories],
  );

  const data = useMemo(() => {
    return AGE_GROUPS.map(age => {
      let female = 0, male = 0;
      for (const s of filtered) {
        female += s.gender_f[age] ?? 0;
        male += s.gender_m[age] ?? 0;
      }
      return { age, female, male };
    });
  }, [filtered]);

  useEffect(() => {
    const el = ref.current;
    if (!el || data.length === 0) return;

    const width = containerWidth || el.getBoundingClientRect().width || 340;
    const height = 210;
    const margin = { top: 22, right: 12, bottom: 28, left: 52 };
    const iw = width - margin.left - margin.right;
    const ih = height - margin.top - margin.bottom;

    d3.select(el).selectAll('*').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

    const x0 = d3.scaleBand().domain(AGE_GROUPS).range([0, iw]).padding(0.25);
    const x1 = d3.scaleBand().domain(['female', 'male']).range([0, x0.bandwidth()]).padding(0.08);
    const allMax = d3.max(data, d => Math.max(d.female, d.male)) ?? 1;
    const y = d3.scaleLinear().domain([0, allMax]).nice().range([ih, 0]);

    g.append('g').attr('transform', `translate(0,${ih})`)
      .call(d3.axisBottom(x0).tickSize(0))
      .selectAll('text').style('font-size', '9px').style('fill', '#94a3b8');

    g.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(fmtAxisWon))
      .selectAll('text').style('font-size', '9px').style('fill', '#64748b');

    g.selectAll('.domain').remove();

    const femaleColor = '#f472b6';
    const maleColor = '#60a5fa';
    const activeDemoAge = settings.demographic !== 'all' ? settings.demographic.slice(2) + '대' : null;
    const activeDemoGender = settings.demographic !== 'all' ? settings.demographic[0] : null;

    data.forEach(d => {
      const xBase = x0(d.age)!;

      g.append('rect')
        .attr('class', 'demo-bar')
        .attr('data-label', d.age + ' 여성')
        .attr('data-val', d.female)
        .attr('x', xBase + x1('female')!)
        .attr('y', y(d.female))
        .attr('width', x1.bandwidth())
        .attr('height', ih - y(d.female))
        .attr('fill', femaleColor)
        .attr('rx', 2)
        .attr('opacity', activeDemoAge === d.age && activeDemoGender === 'f' ? 1 : activeDemoAge ? 0.3 : 0.8);

      g.append('rect')
        .attr('class', 'demo-bar')
        .attr('data-label', d.age + ' 남성')
        .attr('data-val', d.male)
        .attr('x', xBase + x1('male')!)
        .attr('y', y(d.male))
        .attr('width', x1.bandwidth())
        .attr('height', ih - y(d.male))
        .attr('fill', maleColor)
        .attr('rx', 2)
        .attr('opacity', activeDemoAge === d.age && activeDemoGender === 'm' ? 1 : activeDemoAge ? 0.3 : 0.8);
    });

    const tooltip = d3.select(el).append('div').attr('class', 'chart-tip');
    g.selectAll('.demo-bar').style('cursor', 'pointer')
      .on('mouseenter', function() {
        const label = d3.select(this).attr('data-label');
        const val = d3.select(this).attr('data-val');
        tooltip.style('opacity', '1').html(`<b>${label}</b><br/>${fmtWon(Number(val))}원`);
      })
      .on('mousemove', function(event: MouseEvent) {
        const [mx, my] = d3.pointer(event, el);
        tooltip.style('left', (mx + 12) + 'px').style('top', (my - 10) + 'px');
      })
      .on('mouseleave', () => tooltip.style('opacity', '0'));

    const legend = svg.append('g').attr('transform', `translate(${margin.left + iw - 90},2)`);
    [{ label: '여성', color: femaleColor }, { label: '남성', color: maleColor }].forEach((item, i) => {
      legend.append('rect').attr('x', i * 45).attr('y', 0).attr('width', 8).attr('height', 8)
        .attr('fill', item.color).attr('rx', 2);
      legend.append('text').attr('x', i * 45 + 11).attr('y', 8)
        .text(item.label).style('font-size', '9px').style('fill', '#94a3b8');
    });
  }, [data, settings.demographic, containerWidth]);

  return <div ref={ref} className="chart-container" style={{ minHeight: 210 }} />;
}
