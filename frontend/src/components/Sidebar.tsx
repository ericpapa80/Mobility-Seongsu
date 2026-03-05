import { useState } from 'react';
import type { ViewTab } from './Header';
import './Sidebar.css';

export type FoottrafficMetric = 'acost' | 'cost' | 'grade' | 'per';
export type FoottrafficMode = 'density' | 'polyline' | 'both';
export interface FoottrafficSettings {
  metric: FoottrafficMetric;
  mode: FoottrafficMode;
  intensity: number;
  opacity: number;
  radius: number;
  dayweek: string;
  agrde: string;
}
export const DEFAULT_FT_SETTINGS: FoottrafficSettings = {
  metric: 'acost',
  mode: 'both',
  intensity: 2.0,
  opacity: 0.8,
  radius: 50,
  dayweek: '1',
  agrde: '00',
};

export type StoreSizeBy = 'peco_total' | 'peco_individual' | 'peco_foreign' | 'time_slot' | 'demographic';
export type StoreMode = 'point' | 'density' | 'both';
export interface StoreSettings {
  mode: StoreMode;
  categories: string[];
  sizeBy: StoreSizeBy;
  timeSlot: string;
  demographic: string;
  opacity: number;
  intensity: number;
  radius: number;
}
export const DEFAULT_STORE_SETTINGS: StoreSettings = {
  mode: 'point',
  categories: ['음식', '소매', '서비스'],
  sizeBy: 'peco_total',
  timeSlot: '종일',
  demographic: 'all',
  opacity: 0.85,
  intensity: 2.0,
  radius: 40,
};

export type TrafficMode = 'pattern' | 'realtime';

export interface LayerVisibility {
  bus: boolean;
  traffic: boolean;
  subway: boolean;
  risk: boolean;
  bike: boolean;
  store: boolean;
  building: boolean;
  salary: boolean;
  foottraffic: boolean;
  krafton: boolean;
  commercialArea: boolean;
  commercialAreaLabel: boolean;
  commercialAreaChart: boolean;
}

interface Props {
  layers: LayerVisibility;
  onToggle: (key: keyof LayerVisibility) => void;
  activeView: ViewTab;
  foottrafficSettings: FoottrafficSettings;
  onFoottrafficSettings: (s: FoottrafficSettings) => void;
  storeSettings: StoreSettings;
  onStoreSettings: (s: StoreSettings) => void;
  trafficMode: TrafficMode;
  onTrafficModeChange: (m: TrafficMode) => void;
  trafficRealtimeTime?: number | null;
}

interface LayerConfigItem { key: keyof LayerVisibility; label: string; icon: string; color: string }
interface LayerGroup { group: string; kind: 'tab' | 'shared'; items: LayerConfigItem[] }

const LAYER_GROUPS: LayerGroup[] = [
  { group: '유동 흐름', kind: 'tab', items: [
    { key: 'traffic', label: '교통 속도', icon: 'ri-road-map-line', color: 'var(--accent-red)' },
    { key: 'bus', label: '버스 정류장', icon: 'ri-bus-2-line', color: 'var(--accent-blue)' },
    { key: 'subway', label: '지하철 (역사·출구)', icon: 'ri-train-line', color: 'var(--accent-green)' },
    { key: 'foottraffic', label: '보행자 통행량', icon: 'ri-footprint-line', color: '#f59e0b' },
    { key: 'bike', label: '공유 자전거', icon: 'ri-riding-line', color: 'var(--accent-green)' },
  ]},
  { group: '상권', kind: 'shared', items: [
    { key: 'commercialArea', label: '상권 경계', icon: 'ri-store-3-line', color: '#06b6d4' },
    { key: 'store', label: '상가 분포', icon: 'ri-store-2-line', color: '#fb923c' },
    { key: 'salary', label: '사업장/급여', icon: 'ri-money-dollar-circle-line', color: '#3b82f6' },
    { key: 'krafton', label: '크래프톤 클러스터', icon: 'ri-map-pin-range-line', color: '#ec4899' },
    { key: 'building', label: '건물 3D', icon: 'ri-building-line', color: '#8b5cf6' },
  ]},
  { group: '안전', kind: 'tab', items: [
    { key: 'risk', label: '위험 구간', icon: 'ri-error-warning-line', color: 'var(--accent-red)' },
  ]},
];

const VIEW_TO_GROUPS: Record<ViewTab, string[]> = {
  flow: ['유동 흐름', '상권'],
  infrastructure: ['상권'],
  risk: ['안전', '상권'],
};

const KPI_CARDS: { label: string; value: string; change: string; positive: boolean; icon: string; gradient: string }[] = [
  { label: '일평균 통행량', value: '47,320', change: '+3.2%', positive: true, icon: 'ri-route-line', gradient: 'var(--gradient-blue)' },
  { label: '평균 혼잡도', value: '0.72', change: '+0.05', positive: false, icon: 'ri-speed-line', gradient: 'var(--gradient-amber)' },
  { label: '대중교통 분담률', value: '64.3%', change: '+1.8%', positive: true, icon: 'ri-bus-line', gradient: 'var(--gradient-green)' },
  { label: '사고 위험지수', value: '23.5', change: '-5.1', positive: true, icon: 'ri-alert-line', gradient: 'var(--gradient-red)' },
];

interface DataSource {
  name: string;
  status: 'active' | 'inactive';
  lastUpdate: string;
}
const DATA_SOURCES: DataSource[] = [
  { name: '서울 열린데이터', status: 'active', lastUpdate: '2시간 전' },
  { name: 'SK Open API', status: 'active', lastUpdate: '실시간' },
  { name: 'SGIS 통계', status: 'active', lastUpdate: '일 1회' },
  { name: '카카오 모빌리티', status: 'active', lastUpdate: '30분 전' },
  { name: 'OpenUp 상권분석', status: 'active', lastUpdate: '월 1회' },
  { name: '국민연금 사업장', status: 'inactive', lastUpdate: '점검 중' },
  { name: '건축 데이터 Hub', status: 'active', lastUpdate: '주 1회' },
];

const METRIC_OPTIONS: { value: FoottrafficMetric; label: string }[] = [
  { value: 'acost', label: '추정 통행량' },
  { value: 'cost', label: '보정 통행량' },
  { value: 'grade', label: '등급' },
  { value: 'per', label: '혼잡율(%)' },
];

const MODE_OPTIONS: { value: FoottrafficMode; label: string }[] = [
  { value: 'density', label: '밀도' },
  { value: 'polyline', label: '폴리라인' },
  { value: 'both', label: '밀도+라인' },
];

const DAYWEEK_OPTIONS: { value: string; label: string }[] = [
  { value: '1', label: '평일' },
  { value: '2', label: '주말' },
];

const AGRDE_OPTIONS: { value: string; label: string }[] = [
  { value: '00', label: '전체' },
  { value: '10', label: '10대' },
  { value: '20', label: '20대' },
  { value: '30', label: '30대' },
  { value: '40', label: '40대' },
  { value: '50', label: '50대' },
  { value: '60', label: '60+' },
];

const STORE_CATEGORIES: { value: string; label: string; css: string }[] = [
  { value: '음식', label: '음식', css: 'cat-food' },
  { value: '소매', label: '소매', css: 'cat-retail' },
  { value: '서비스', label: '서비스', css: 'cat-service' },
];

const STORE_SIZE_OPTIONS: { value: StoreSizeBy; label: string }[] = [
  { value: 'peco_total', label: '전체매출' },
  { value: 'peco_individual', label: '개인매출' },
  { value: 'peco_foreign', label: '외국인매출' },
  { value: 'time_slot', label: '시간대별' },
  { value: 'demographic', label: '성별/연령' },
];

const STORE_TIME_OPTIONS: { value: string; label: string }[] = [
  { value: '종일', label: '종일' },
  { value: '아침', label: '아침' },
  { value: '점심', label: '점심' },
  { value: '오후', label: '오후' },
  { value: '저녁', label: '저녁' },
  { value: '밤', label: '밤' },
  { value: '심야', label: '심야' },
  { value: '새벽', label: '새벽' },
];

const STORE_DEMO_OPTIONS: { value: string; label: string }[] = [
  { value: 'all', label: '전체' },
  { value: 'f_20', label: '여20' }, { value: 'f_30', label: '여30' },
  { value: 'f_40', label: '여40' }, { value: 'f_50', label: '여50' },
  { value: 'f_60', label: '여60' },
  { value: 'm_20', label: '남20' }, { value: 'm_30', label: '남30' },
  { value: 'm_40', label: '남40' }, { value: 'm_50', label: '남50' },
  { value: 'm_60', label: '남60' },
];

const STORE_MODE_OPTIONS: { value: StoreMode; label: string }[] = [
  { value: 'point', label: '포인트' },
  { value: 'density', label: '밀도' },
  { value: 'both', label: '포인트+밀도' },
];

function StoreSubPanel({ settings, onChange }: { settings: StoreSettings; onChange: (s: StoreSettings) => void }) {
  const set = (patch: Partial<StoreSettings>) => onChange({ ...settings, ...patch });
  const toggleCat = (cat: string) => {
    const cats = settings.categories.includes(cat)
      ? settings.categories.filter(c => c !== cat)
      : [...settings.categories, cat];
    if (cats.length > 0) set({ categories: cats });
  };
  const showDensity = settings.mode === 'density' || settings.mode === 'both';
  return (
    <div className="lp-sub-panel">
      <div className="lp-row">
        <span className="lp-label">업종</span>
        <div className="lp-btn-group">
          {STORE_CATEGORIES.map(c => (
            <button key={c.value}
              className={`lp-btn ${c.css}${settings.categories.includes(c.value) ? '' : ' inactive'}`}
              onClick={() => toggleCat(c.value)}>{c.label}</button>
          ))}
        </div>
      </div>
      <div className="lp-row">
        <span className="lp-label">크기</span>
        <div className="lp-btn-group">
          {STORE_SIZE_OPTIONS.map(o => (
            <button key={o.value}
              className={`lp-btn store-accent${settings.sizeBy === o.value ? ' active' : ''}`}
              onClick={() => set({ sizeBy: o.value })}>{o.label}</button>
          ))}
        </div>
      </div>
      {(settings.sizeBy === 'time_slot') && (
        <div className="lp-row">
          <span className="lp-label" style={{ fontSize: '9px', color: '#64748b' }}>시간대 슬라이더와 연동됩니다</span>
        </div>
      )}
      {(settings.sizeBy === 'demographic') && (
        <div className="lp-row">
          <span className="lp-label">인구</span>
          <div className="lp-btn-group">
            {STORE_DEMO_OPTIONS.map(o => (
              <button key={o.value}
                className={`lp-btn store-accent${settings.demographic === o.value ? ' active' : ''}`}
                onClick={() => set({ demographic: o.value })}>{o.label}</button>
            ))}
          </div>
        </div>
      )}
      <div className="lp-divider" />
      <div className="lp-row">
        <span className="lp-label">표현</span>
        <div className="lp-btn-group">
          {STORE_MODE_OPTIONS.map(o => (
            <button key={o.value}
              className={`lp-btn store-accent${settings.mode === o.value ? ' active' : ''}`}
              onClick={() => set({ mode: o.value })}>{o.label}</button>
          ))}
        </div>
      </div>
      {showDensity && (
        <>
          <div className="lp-row">
            <span className="lp-label">밀도 강도</span>
            <input type="range" min="0.5" max="5" step="0.25" value={settings.intensity}
              onChange={e => set({ intensity: +e.target.value })} className="lp-slider store-accent" />
            <span className="lp-val">{settings.intensity.toFixed(1)}</span>
          </div>
          <div className="lp-row">
            <span className="lp-label">밀도 반경</span>
            <input type="range" min="20" max="120" step="5" value={settings.radius}
              onChange={e => set({ radius: +e.target.value })} className="lp-slider store-accent" />
            <span className="lp-val">{settings.radius}px</span>
          </div>
        </>
      )}
      <div className="lp-row">
        <span className="lp-label">투명도</span>
        <input type="range" min="0.1" max="1" step="0.05" value={settings.opacity}
          onChange={e => set({ opacity: +e.target.value })} className="lp-slider store-accent" />
        <span className="lp-val">{Math.round(settings.opacity * 100)}%</span>
      </div>
    </div>
  );
}

export default function Sidebar({ layers, onToggle, activeView, foottrafficSettings, onFoottrafficSettings, storeSettings, onStoreSettings, trafficMode, onTrafficModeChange, trafficRealtimeTime }: Props) {
  const safetyScore = activeView === 'risk' ? 72 : null;
  const [ftExpanded, setFtExpanded] = useState(false);
  const [stExpanded, setStExpanded] = useState(false);
  const [caExpanded, setCaExpanded] = useState(false);
  const fts = foottrafficSettings;
  const setFts = (patch: Partial<FoottrafficSettings>) => onFoottrafficSettings({ ...fts, ...patch });
  const sts = storeSettings;
  const setSts = (s: StoreSettings) => onStoreSettings(s);

  return (
    <aside className="sidebar">
      {/* KPI Cards */}
      <div className="sidebar-section kpi-section">
        <div className="sidebar-section-title">핵심 지표 (KPI)</div>
        <div className="kpi-grid">
          {KPI_CARDS.map((k) => (
            <div key={k.label} className="kpi-card">
              <div className="kpi-icon" style={{ background: k.gradient }}>
                <i className={k.icon} />
              </div>
              <div className="kpi-info">
                <span className="kpi-label">{k.label}</span>
                <span className="kpi-value">{k.value}</span>
                <span className={`kpi-change ${k.positive ? 'positive' : 'negative'}`}>
                  {k.change}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Safety Score Gauge (shown in Risk view) */}
      {safetyScore !== null && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">안전 종합 지수</div>
          <div className="gauge-container">
            <svg viewBox="0 0 120 70" className="gauge-svg">
              <path d="M10 65 A50 50 0 0 1 110 65" fill="none" stroke="var(--border)" strokeWidth="8" strokeLinecap="round" />
              <path
                d="M10 65 A50 50 0 0 1 110 65"
                fill="none"
                stroke="var(--accent-green)"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${(safetyScore / 100) * 157} 157`}
              />
            </svg>
            <div className="gauge-value">{safetyScore}<span className="gauge-unit">/100</span></div>
            <div className="gauge-label">양호</div>
          </div>
        </div>
      )}

      {/* Layer Controls */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">레이어 제어</div>
        {(() => {
          const allowed = VIEW_TO_GROUPS[activeView];
          const visible = LAYER_GROUPS.filter(g => allowed.includes(g.group));
          const hasTabGroup = visible.some(g => g.kind === 'tab');
          let dividerInserted = false;
          return visible.map((grp) => {
            const showDivider = hasTabGroup && grp.kind === 'shared' && !dividerInserted;
            if (showDivider) dividerInserted = true;
            return (
              <div key={grp.group}>
                {showDivider && <hr className="layer-group-divider" />}
                <div className="layer-group-title">{grp.group}</div>
                {grp.items.map((l) => (
                  <div key={l.key}>
                    <div
                      className={`layer-toggle${layers[l.key] ? ' active' : ''}`}
                      onClick={() => onToggle(l.key)}
                    >
                      <i className={l.icon} style={{ color: l.color }} />
                      <span>{l.label}</span>
                      {l.key === 'foottraffic' && layers.foottraffic && (
                        <span className="lp-expand-btn" role="button" tabIndex={0}
                          onClick={(e) => { e.stopPropagation(); setFtExpanded(p => !p); }} title="세부 설정">
                          <i className={ftExpanded ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'} />
                        </span>
                      )}
                      {l.key === 'store' && layers.store && (
                        <span className="lp-expand-btn" role="button" tabIndex={0}
                          onClick={(e) => { e.stopPropagation(); setStExpanded(p => !p); }} title="세부 설정">
                          <i className={stExpanded ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'} />
                        </span>
                      )}
                      {l.key === 'commercialArea' && layers.commercialArea && (
                        <span className="lp-expand-btn" role="button" tabIndex={0}
                          onClick={(e) => { e.stopPropagation(); setCaExpanded(p => !p); }} title="세부 설정">
                          <i className={caExpanded ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'} />
                        </span>
                      )}
                      <div className={`toggle-switch${layers[l.key] ? ' on' : ''}`} />
                    </div>

                    {l.key === 'traffic' && layers.traffic && (
                      <div className="lp-sub-panel">
                        <div className="lp-row">
                          <span className="lp-label">모드</span>
                          <div className="lp-btn-group">
                            <button className={`lp-btn${trafficMode === 'pattern' ? ' active' : ''}`}
                              onClick={() => onTrafficModeChange('pattern')}>패턴</button>
                            <button className={`lp-btn${trafficMode === 'realtime' ? ' active' : ''}`}
                              onClick={() => onTrafficModeChange('realtime')}>실시간</button>
                          </div>
                        </div>
                        {trafficMode === 'realtime' && (
                          <div className="lp-row">
                            <span className="lp-label" style={{ fontSize: '9px', color: '#94a3b8' }}>
                              {trafficRealtimeTime
                                ? `갱신: ${new Date(trafficRealtimeTime * 1000).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })} · 5분 주기`
                                : '갱신 주기: 5분'}
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                    {l.key === 'commercialArea' && layers.commercialArea && caExpanded && (
                      <div className="lp-sub-panel">
                        <div className="lp-row">
                          <span className="lp-label">레이블</span>
                          <div
                            className={`toggle-switch mini${layers.commercialAreaLabel ? ' on' : ''}`}
                            onClick={() => onToggle('commercialAreaLabel')}
                            role="button" tabIndex={0}
                          />
                        </div>
                      </div>
                    )}

                    {l.key === 'foottraffic' && layers.foottraffic && ftExpanded && (
                      <div className="lp-sub-panel">
                        <div className="lp-row">
                          <span className="lp-label">주간</span>
                          <div className="lp-btn-group">
                            {DAYWEEK_OPTIONS.map(o => (
                              <button key={o.value} className={`lp-btn${fts.dayweek === o.value ? ' active' : ''}`}
                                onClick={() => setFts({ dayweek: o.value })}>{o.label}</button>
                            ))}
                          </div>
                        </div>
                        <div className="lp-row">
                          <span className="lp-label">연령대</span>
                          <div className="lp-btn-group">
                            {AGRDE_OPTIONS.map(o => (
                              <button key={o.value} className={`lp-btn${fts.agrde === o.value ? ' active' : ''}`}
                                onClick={() => setFts({ agrde: o.value })}>{o.label}</button>
                            ))}
                          </div>
                        </div>
                        <div className="lp-divider" />
                        <div className="lp-row">
                          <span className="lp-label">속성</span>
                          <div className="lp-btn-group">
                            {METRIC_OPTIONS.map(o => (
                              <button key={o.value} className={`lp-btn${fts.metric === o.value ? ' active' : ''}`}
                                onClick={() => setFts({ metric: o.value })}>{o.label}</button>
                            ))}
                          </div>
                        </div>
                        <div className="lp-row">
                          <span className="lp-label">표현</span>
                          <div className="lp-btn-group">
                            {MODE_OPTIONS.map(o => (
                              <button key={o.value} className={`lp-btn${fts.mode === o.value ? ' active' : ''}`}
                                onClick={() => setFts({ mode: o.value })}>{o.label}</button>
                            ))}
                          </div>
                        </div>
                        <div className="lp-divider" />
                        <div className="lp-row">
                          <span className="lp-label">밀도 강도</span>
                          <input type="range" min="0.5" max="5" step="0.25" value={fts.intensity}
                            onChange={e => setFts({ intensity: +e.target.value })} className="lp-slider" />
                          <span className="lp-val">{fts.intensity.toFixed(1)}</span>
                        </div>
                        <div className="lp-row">
                          <span className="lp-label">투명도</span>
                          <input type="range" min="0.1" max="1" step="0.05" value={fts.opacity}
                            onChange={e => setFts({ opacity: +e.target.value })} className="lp-slider" />
                          <span className="lp-val">{Math.round(fts.opacity * 100)}%</span>
                        </div>
                        <div className="lp-row">
                          <span className="lp-label">밀도 반경</span>
                          <input type="range" min="20" max="120" step="5" value={fts.radius}
                            onChange={e => setFts({ radius: +e.target.value })} className="lp-slider" />
                          <span className="lp-val">{fts.radius}px</span>
                        </div>
                      </div>
                    )}

                    {l.key === 'store' && layers.store && stExpanded && (
                      <StoreSubPanel settings={sts} onChange={setSts} />
                    )}
                  </div>
                ))}
              </div>
            );
          });
        })()}
      </div>

      {/* Data Sources */}
      <div className="sidebar-section">
        <div className="sidebar-section-title">데이터 수집 현황</div>
        {DATA_SOURCES.map((s) => (
          <div key={s.name} className="source-row">
            <div className="source-left">
              <span className={`source-dot ${s.status}`} />
              <span className="source-name">{s.name}</span>
            </div>
            <span className="source-meta">{s.lastUpdate}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
