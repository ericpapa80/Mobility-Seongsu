import { useState, useMemo } from 'react';
import { Map } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, PathLayer, TextLayer } from '@deck.gl/layers';
import type { MapViewState } from '@deck.gl/core';
import './Strategy.css';

const BASEMAP = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

const INITIAL_VIEW: MapViewState = {
  longitude: 127.056,
  latitude: 37.5445,
  zoom: 14.5,
  pitch: 0,
  bearing: 0,
};

interface PolicyConfig {
  id: string;
  name: string;
  desc: string;
  color: string;
  active: boolean;
}

const BRT_ROUTE = [
  [127.053, 37.542],
  [127.056, 37.5445],
  [127.058, 37.546],
  [127.060, 37.548],
  [127.063, 37.549],
];

const SHARING_HUBS = [
  { lng: 127.0560, lat: 37.5445, name: '성수역 거점', isNew: false },
  { lng: 127.0430, lat: 37.5476, name: '뚝섬역 거점', isNew: false },
  { lng: 127.0648, lat: 37.5485, name: '서울숲역 거점', isNew: false },
  { lng: 127.0580, lat: 37.5430, name: 'IT밸리 신규', isNew: true },
  { lng: 127.0500, lat: 37.5510, name: '서울숲공원 신규', isNew: true },
];

const GREEN_ZONES = [
  { lng: 127.056, lat: 37.5445, radius: 350, name: '성수역 주변' },
  { lng: 127.058, lat: 37.546, radius: 250, name: '카페거리' },
  { lng: 127.043, lat: 37.5476, radius: 200, name: '뚝섬역 주변' },
];

export default function Strategy() {
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW);
  const [policies, setPolicies] = useState<PolicyConfig[]>([
    { id: 'A', name: '정책 A: BRT 도입', desc: '성수대교~서울숲 간 간선급행 노선', color: '#3b82f6', active: true },
    { id: 'B', name: '정책 B: 공유모빌리티', desc: '거점 5개소 + 킥보드/자전거 연계', color: '#10b981', active: true },
    { id: 'C', name: '정책 C: 그린존', desc: '보행자 우선 구역 지정 (차량 제한)', color: '#8b5cf6', active: true },
  ]);

  const togglePolicy = (id: string) => {
    setPolicies(prev => prev.map(p => p.id === id ? { ...p, active: !p.active } : p));
  };

  const policyA = policies.find(p => p.id === 'A')!;
  const policyB = policies.find(p => p.id === 'B')!;
  const policyC = policies.find(p => p.id === 'C')!;

  const layers = useMemo(() => [
    policyA.active && new PathLayer({
      id: 'brt-route',
      data: [{ path: BRT_ROUTE }],
      getPath: (d: { path: number[][] }) => d.path,
      getColor: [59, 130, 246, 200],
      getWidth: 8,
      widthUnits: 'pixels' as const,
      capRounded: true,
    }),

    policyB.active && new ScatterplotLayer({
      id: 'sharing-hubs',
      data: SHARING_HUBS,
      getPosition: (d: typeof SHARING_HUBS[0]) => [d.lng, d.lat],
      getRadius: 40,
      radiusUnits: 'meters' as const,
      getFillColor: (d: typeof SHARING_HUBS[0]) =>
        d.isNew
          ? [16, 185, 129, 220] as [number, number, number, number]
          : [16, 185, 129, 120] as [number, number, number, number],
      getLineColor: [255, 255, 255, 180] as [number, number, number, number],
      lineWidthMinPixels: 2,
      stroked: true,
      pickable: true,
    }),

    policyB.active && new TextLayer({
      id: 'sharing-labels',
      data: SHARING_HUBS,
      getPosition: (d: typeof SHARING_HUBS[0]) => [d.lng, d.lat],
      getText: (d: typeof SHARING_HUBS[0]) => d.name,
      getSize: 11,
      getColor: [16, 185, 129, 255],
      getPixelOffset: [0, -18],
      fontFamily: 'Pretendard, sans-serif',
      fontWeight: 600,
    }),

    policyC.active && new ScatterplotLayer({
      id: 'green-zones',
      data: GREEN_ZONES,
      getPosition: (d: typeof GREEN_ZONES[0]) => [d.lng, d.lat],
      getRadius: (d: typeof GREEN_ZONES[0]) => d.radius,
      radiusUnits: 'meters' as const,
      getFillColor: [139, 92, 246, 30] as [number, number, number, number],
      getLineColor: [139, 92, 246, 100] as [number, number, number, number],
      lineWidthMinPixels: 1,
      stroked: true,
    }),
  ].filter(Boolean), [policyA.active, policyB.active, policyC.active]);

  return (
    <div className="strategy">
      <aside className="strategy-sidebar">
        <div className="sidebar-section">
          <div className="sidebar-section-title">정책 시나리오</div>
          {policies.map(p => (
            <div
              key={p.id}
              className={`policy-card${p.active ? ' active' : ''}`}
              style={{ borderColor: p.active ? p.color : undefined }}
              onClick={() => togglePolicy(p.id)}
            >
              <div className="policy-card-header">
                <span className="policy-name">{p.name}</span>
                <span className="policy-tag" style={{ background: p.color }}>{p.id}</span>
              </div>
              <p className="policy-desc">{p.desc}</p>
            </div>
          ))}
        </div>

        <div className="sidebar-section">
          <div className="sidebar-section-title">기대 효과</div>
          <div className="effect-item">
            <span className="effect-label">교통 혼잡 감소</span>
            <span className="effect-value positive">-18%</span>
          </div>
          <div className="effect-item">
            <span className="effect-label">보행 안전성 향상</span>
            <span className="effect-value positive">+24%</span>
          </div>
          <div className="effect-item">
            <span className="effect-label">대중교통 분담률</span>
            <span className="effect-value positive">+12%</span>
          </div>
          <div className="effect-item">
            <span className="effect-label">탄소 배출 감소</span>
            <span className="effect-value positive">-15%</span>
          </div>
        </div>
      </aside>

      <div className="strategy-map">
        <DeckGL
          viewState={viewState}
          onViewStateChange={(e) => setViewState(e.viewState as MapViewState)}
          controller
          layers={layers}
        >
          <Map mapStyle={BASEMAP} />
        </DeckGL>
      </div>
    </div>
  );
}
