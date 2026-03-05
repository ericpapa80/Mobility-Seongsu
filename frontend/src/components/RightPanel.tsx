import { useState, useCallback } from 'react';
import type { ViewTab } from './Header';
import type {
  BusStopHourly, BusStopHourlyFull, SubwayStationHourly,
  TrafficSegment, TrafficRealtimeSegment, TrafficPatternResponse,
  FoottrafficResponse, Store, SalaryResponse,
  GeoJSONCollection,
} from '../api/client';
import type { LayerVisibility, FoottrafficSettings, StoreSettings, TrafficMode } from './Sidebar';
import BusRidershipChart from './BusRidershipChart';

import PedDensityTrendChart from './PedDensityTrendChart';
import BusStopHourlyChart from './BusStopHourlyChart';
import SubwayExitChart from './SubwayExitChart';
import SubwayRidershipChart from './SubwayRidershipChart';
import type { RidershipMode } from './SubwayRidershipChart';

import SafetyRadarChart from './SafetyRadarChart';
import SensitivityChart from './SensitivityChart';
import TrafficSpeedChart from './TrafficSpeedChart';
import FoottrafficDensityChart from './FoottrafficDensityChart';
import SalaryDistributionChart from './SalaryDistributionChart';
import StoreDrillChart from './StoreDrillChart';
import type { DrillState } from './StoreDrillChart';
import StoreWeekdayChart from './StoreWeekdayChart';
import StoreDemoChart from './StoreDemoChart';
import StoreFamChart from './StoreFamChart';
import StorePecoChart from './StorePecoChart';
import StoreWdweChart from './StoreWdweChart';
import StoreRevfreqChart from './StoreRevfreqChart';
import StoreTrendChart from './StoreTrendChart';
import AreaWorkplaceChart from './AreaWorkplaceChart';
import AreaFoottrafficChart from './AreaFoottrafficChart';
import AreaBusChart from './AreaBusChart';
import './RightPanel.css';

interface Props {
  activeView: ViewTab;
  busStops: BusStopHourly[];
  busStopsFull: BusStopHourlyFull[];
  subwayHourlyStations: SubwayStationHourly[];
  trafficSegments: TrafficSegment[];
  foottrafficData: FoottrafficResponse | null;
  stores: Store[];
  storeSettings: StoreSettings;
  salaryData: SalaryResponse | null;
  commercialAreaGeoJson: GeoJSONCollection | null;
  layerVisibility: LayerVisibility;
  foottrafficSettings: FoottrafficSettings;
  currentHour: number;
  collapsed: boolean;
  onToggle: () => void;
  expanded: boolean;
  onExpandToggle: () => void;
  onDrillStateChange?: (state: DrillState) => void;
  trafficMode?: TrafficMode;
  trafficRealtimeSegments?: TrafficRealtimeSegment[];
  trafficPatternData?: TrafficPatternResponse | null;
}

type BusChartMode = 'ride' | 'alight' | 'total';

const VIEW_TITLES: Record<ViewTab, string> = {
  infrastructure: '인프라 분석 (준비중)',
  flow: '유동 흐름 분석',
  risk: '위험도 분석',
};

/* ── Shared Charts (모든 탭 공통: 상권 레이어) ── */
function SharedCharts({ lv, stores, storeSettings, salaryData, commercialAreaGeoJson, foottrafficSettings, foottrafficData, busStopsFull, currentHour, onDrillStateChange, expanded }: {
  lv: LayerVisibility;
  stores: Store[];
  storeSettings: StoreSettings;
  salaryData: SalaryResponse | null;
  commercialAreaGeoJson: GeoJSONCollection | null;
  foottrafficSettings: FoottrafficSettings;
  foottrafficData: FoottrafficResponse | null;
  busStopsFull: BusStopHourlyFull[];
  currentHour: number;
  onDrillStateChange?: (state: DrillState) => void;
  expanded?: boolean;
}) {
  const [drillFiltered, setDrillFiltered] = useState<{ stores: Store[]; settings: StoreSettings; drill: DrillState } | null>(null);

  const handleFilteredChange = useCallback((filteredStores: Store[], filteredSettings: StoreSettings, drill: DrillState) => {
    setDrillFiltered({ stores: filteredStores, settings: filteredSettings, drill });
  }, []);

  const rightStores = drillFiltered?.stores ?? stores;
  const rightSettings = drillFiltered?.settings ?? storeSettings;
  const hasBreadcrumb = drillFiltered ? drillFiltered.drill.level !== 'all' : false;

  const hasStore = lv.store && stores.length > 0;
  const hasAreaAgg = lv.commercialArea && commercialAreaGeoJson;
  const hasAny = lv.store || lv.salary || lv.krafton || lv.commercialArea || lv.building || lv.foottraffic || lv.bus;
  if (!hasAny) return null;

  return (
    <>
      {/* ── 성수동 집계 (드릴다운) ── */}
      {hasStore && !expanded && (
        <ChartCard title="상가 매출 분석" subtitle="클릭하여 드릴다운 · 2025.10 기준">
          <StoreDrillChart
            stores={stores}
            settings={storeSettings}
            currentHour={currentHour}
            commercialAreaGeoJson={commercialAreaGeoJson}
            onDrillStateChange={onDrillStateChange}
          />
        </ChartCard>
      )}
      {hasStore && expanded && (
        <ChartCard title="상가 매출 분석" subtitle="클릭하여 드릴다운 · 2025.10 기준">
          <div className="store-expanded-grid">
            <div className="store-expanded-col">
              <StoreDrillChart
                stores={stores}
                settings={storeSettings}
                currentHour={currentHour}
                commercialAreaGeoJson={commercialAreaGeoJson}
                onDrillStateChange={onDrillStateChange}
                onFilteredChange={handleFilteredChange}
                expanded
              />
            </div>
            <div className="store-expanded-col">
              <div className="drill-top">
                {hasBreadcrumb && <div className="drill-breadcrumb-spacer" />}
                <div className="drill-sub-title" style={{ marginTop: 0 }}>요일별 매출</div>
                <StoreWeekdayChart stores={rightStores} settings={rightSettings} />
              </div>
              <div className="drill-aux">
                <div className="drill-sub-title" style={{ marginTop: 0 }}>성별연령별 매출</div>
                <StoreDemoChart stores={rightStores} settings={rightSettings} />
              </div>
            </div>
          </div>
          <div className="store-expanded-grid" style={{ marginTop: 16 }}>
            <div className="store-expanded-col">
              <div className="drill-sub-title" style={{ marginTop: 0 }}>세대별 매출</div>
              <StoreFamChart stores={rightStores} settings={rightSettings} />
              <div className="drill-sub-title">소비자 유형별 매출</div>
              <StorePecoChart stores={rightStores} settings={rightSettings} />
              <div className="drill-sub-title">재방문 빈도</div>
              <StoreRevfreqChart stores={rightStores} settings={rightSettings} />
            </div>
            <div className="store-expanded-col">
              <div className="drill-sub-title" style={{ marginTop: 0 }}>평일/공휴일 매출</div>
              <StoreWdweChart stores={rightStores} settings={rightSettings} />
              <div className="drill-sub-title">연도별 매출 추이</div>
              <StoreTrendChart stores={rightStores} settings={rightSettings} />
            </div>
          </div>
        </ChartCard>
      )}

      {/* ── 급여/사업장 ── */}
      {lv.salary && salaryData && (
        <ChartCard title="업종별 평균 급여" subtitle="상위 15개">
          <SalaryDistributionChart industries={salaryData.summary.by_industry} />
        </ChartCard>
      )}

      {/* ── 상권별 집계 (상권 경계 레이어 ON 필수) ── */}
      {hasAreaAgg && (
        <>
          {/* 상권별 집계 */}
          {lv.salary && salaryData && (
            <ChartCard title="상권별 사업장/급여" subtitle="사업장 수 · 평균 급여">
              <AreaWorkplaceChart workplaces={salaryData.workplaces} commercialAreaGeoJson={commercialAreaGeoJson!} />
            </ChartCard>
          )}
          {lv.foottraffic && foottrafficData && (
            <ChartCard title="상권별 보행 통행량" subtitle="추정 통행량 합계">
              <AreaFoottrafficChart links={foottrafficData.links} commercialAreaGeoJson={commercialAreaGeoJson!} settings={foottrafficSettings} />
            </ChartCard>
          )}
          {lv.bus && busStopsFull.length > 0 && (
            <ChartCard title="상권별 버스 승하차" subtitle="승차 + 하차 합계">
              <AreaBusChart stops={busStopsFull} commercialAreaGeoJson={commercialAreaGeoJson!} />
            </ChartCard>
          )}
        </>
      )}

    </>
  );
}

export default function RightPanel({ activeView, busStops, busStopsFull, subwayHourlyStations, trafficSegments, foottrafficData, stores, storeSettings, salaryData, commercialAreaGeoJson, layerVisibility, foottrafficSettings, currentHour, collapsed, onToggle, expanded, onExpandToggle, onDrillStateChange, trafficMode = 'pattern', trafficRealtimeSegments = [], trafficPatternData = null }: Props) {
  const lv = layerVisibility;
  const [busMode, setBusMode] = useState<BusChartMode>('total');
  const [busHourlyMode, setBusHourlyMode] = useState<BusChartMode>('total');
  const [subwayRiderMode, setSubwayRiderMode] = useState<RidershipMode>('ridealight');
  const [compare, setCompare] = useState(false);
  const [flowOpen, setFlowOpen] = useState(true);
  const [sharedOpen, setSharedOpen] = useState(true);
  const [safetyOpen, setSafetyOpen] = useState(true);

  const sharedProps = { lv, stores, storeSettings, salaryData, commercialAreaGeoJson, foottrafficSettings, foottrafficData, busStopsFull, currentHour, onDrillStateChange, expanded };

  const panelClass = `right-panel${collapsed ? ' collapsed' : ''}${expanded ? ' expanded' : ''}`;

  return (
    <div className={panelClass}>
      <button className="rp-toggle" onClick={onToggle}>
        <i className={collapsed ? 'ri-arrow-left-s-line' : 'ri-arrow-right-s-line'} />
      </button>

      {!collapsed && (
        <div className="rp-content">
          <div className="rp-header-row">
            <span className="rp-title">{VIEW_TITLES[activeView]}</span>
            <div className="rp-header-actions">
              <button className="rp-expand-btn" onClick={onExpandToggle} title={expanded ? '축소' : '확장'}>
                <i className={expanded ? 'ri-contract-left-right-line' : 'ri-expand-left-right-line'} />
              </button>
              <label className="compare-toggle">
                <input type="checkbox" checked={compare} onChange={() => setCompare(c => !c)} />
                <span className="compare-label">비교</span>
              </label>
            </div>
          </div>

          <div className="rp-charts-grid">
            {/* ── Infrastructure View ── */}
            {activeView === 'infrastructure' && (
              <>
                <div className="chart-card placeholder-infra">
                  <i className="ri-road-map-line" style={{ fontSize: 28, color: 'var(--accent-blue)', marginBottom: 8 }} />
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, textAlign: 'center' }}>
                    보도·차도·어린이보호구역 등<br />하드 인프라 데이터 연동 예정
                  </div>
                </div>
                <SectionHeader title="상권" open={sharedOpen} onToggle={() => setSharedOpen(o => !o)} />
                {sharedOpen && <SharedCharts {...sharedProps} />}
                {!sharedOpen && !lv.store && !lv.salary && !lv.krafton && !lv.commercialArea && !lv.building && (
                  <EmptyHint />
                )}
              </>
            )}

            {/* ── Dynamic Flow View ── */}
            {activeView === 'flow' && (
              <>
                {(lv.traffic || lv.subway || lv.foottraffic || lv.bus || lv.bike) && (
                  <>
                    <SectionHeader title="유동 흐름" open={flowOpen} onToggle={() => setFlowOpen(o => !o)} />
                    {flowOpen && (
                      <>
                        {lv.traffic && (trafficSegments.length > 0 || trafficPatternData) && (
                          <ChartCard
                            title={trafficMode === 'realtime' ? '교통 속도 추이 (실시간 비교)' : '교통 속도 추이 (24시간)'}
                            subtitle={trafficMode === 'realtime' ? '패턴 대비 실시간 속도' : trafficPatternData ? '14개월 TOPIS 패턴' : '성수 평균'}
                          >
                            <TrafficSpeedChart
                              segments={trafficSegments}
                              currentHour={currentHour}
                              trafficMode={trafficMode}
                              realtimeAvgSpeed={
                                trafficMode === 'realtime' && trafficRealtimeSegments.length > 0
                                  ? trafficRealtimeSegments.reduce((sum, s) => sum + s.speed, 0) / trafficRealtimeSegments.length
                                  : null
                              }
                              patternData={trafficPatternData}
                            />
                          </ChartCard>
                        )}
                        {lv.subway && (
                          <>
                            <ChartCard title="지하철 출구별 시간대 흐름" subtitle="출구별 이용인구">
                              <SubwayExitChart stations={subwayHourlyStations} currentHour={currentHour} />
                            </ChartCard>
                            <ChartCard title="지하철 승하차 이용자 구성">
                              <div className="chart-mode-btns">
                                {(['ridealight', 'foreign'] as RidershipMode[]).map(m => (
                                  <button key={m} className={`mode-btn${subwayRiderMode === m ? ' active' : ''}`}
                                    onClick={() => setSubwayRiderMode(m)}>
                                    {m === 'ridealight' ? '승하차' : '외국인'}
                                  </button>
                                ))}
                              </div>
                              <SubwayRidershipChart stations={subwayHourlyStations} mode={subwayRiderMode} currentHour={currentHour} />
                            </ChartCard>
                          </>
                        )}
                        {lv.foottraffic && (
                          <ChartCard title="보행 밀도 변화 추이">
                            <PedDensityTrendChart currentHour={currentHour} />
                          </ChartCard>
                        )}
                        {lv.foottraffic && foottrafficData && (
                          <ChartCard title="보행 통행량 시간대별 분석" subtitle="실측 7개 시간대">
                            <FoottrafficDensityChart data={foottrafficData} currentHour={currentHour} settings={foottrafficSettings} />
                          </ChartCard>
                        )}
                        {lv.bus && (
                          <>
                            <ChartCard title="버스 정류장별 시간대 승하차">
                              <div className="chart-mode-btns">
                                {(['total', 'ride', 'alight'] as BusChartMode[]).map(m => (
                                  <button key={m} className={`mode-btn${busHourlyMode === m ? ' active' : ''}`}
                                    onClick={() => setBusHourlyMode(m)}>
                                    {m === 'total' ? '합산' : m === 'ride' ? '승차' : '하차'}
                                  </button>
                                ))}
                              </div>
                              <BusStopHourlyChart stops={busStopsFull} mode={busHourlyMode} currentHour={currentHour} />
                            </ChartCard>
                            <ChartCard title="버스 승하차 Top 10">
                              <div className="chart-mode-btns">
                                {(['total', 'ride', 'alight'] as BusChartMode[]).map(m => (
                                  <button key={m} className={`mode-btn${busMode === m ? ' active' : ''}`}
                                    onClick={() => setBusMode(m)}>
                                    {m === 'total' ? '합계' : m === 'ride' ? '승차' : '하차'}
                                  </button>
                                ))}
                              </div>
                              <BusRidershipChart stops={busStops} mode={busMode} />
                            </ChartCard>
                          </>
                        )}
                        {lv.bike && (
                          <ChartCard title="공유 모빌리티 현황">
                            <div className="placeholder-chart">
                              <i className="ri-riding-line" />
                              <span>자전거·킥보드 데이터 연동 예정</span>
                            </div>
                          </ChartCard>
                        )}
                      </>
                    )}
                  </>
                )}

                <SectionHeader title="상권" open={sharedOpen} onToggle={() => setSharedOpen(o => !o)} />
                {sharedOpen && <SharedCharts {...sharedProps} />}
              </>
            )}

            {/* ── Risk & Safety View ── */}
            {activeView === 'risk' && (
              <>
                <SectionHeader title="안전" open={safetyOpen} onToggle={() => setSafetyOpen(o => !o)} />
                {safetyOpen && (
                  <>
                    <ChartCard title="안전 지표 레이더">
                      <SafetyRadarChart />
                    </ChartCard>
                    <ChartCard title="위험 이벤트 타임라인">
                      <div className="event-timeline">
                        {SAMPLE_EVENTS.map((ev, i) => (
                          <div key={i} className={`event-row ${ev.severity}`}>
                            <span className="ev-time">{ev.time}</span>
                            <span className="ev-text">{ev.text}</span>
                            <span className={`ev-badge ${ev.severity}`}>{ev.severity === 'high' ? '심각' : ev.severity === 'mid' ? '주의' : '정보'}</span>
                          </div>
                        ))}
                      </div>
                    </ChartCard>
                    <ChartCard title="민감도 분석">
                      <SensitivityChart />
                    </ChartCard>
                  </>
                )}

                <SectionHeader title="상권" open={sharedOpen} onToggle={() => setSharedOpen(o => !o)} />
                {sharedOpen && <SharedCharts {...sharedProps} />}
              </>
            )}

            {compare && (
              <ChartCard title="전월 대비 변화">
                <div className="placeholder-chart">
                  <i className="ri-line-chart-line" />
                  <span>비교 데이터 로딩 중…</span>
                </div>
              </ChartCard>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionHeader({ title, open, onToggle }: { title: string; open: boolean; onToggle: () => void }) {
  return (
    <div className="rp-section-header" onClick={onToggle} role="button" tabIndex={0}>
      <span className="rp-section-title">{title}</span>
      <i className={open ? 'ri-arrow-up-s-line' : 'ri-arrow-down-s-line'} />
    </div>
  );
}

function SubSectionHeader({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rp-sub-section-header">
      <span className="rp-sub-section-title">{title}</span>
      {hint && <span className="rp-sub-section-hint">{hint}</span>}
    </div>
  );
}

function ChartCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <span className="chart-title">{title}</span>
        {subtitle && <span className="chart-subtitle">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function EmptyHint() {
  return (
    <div className="chart-card" style={{ textAlign: 'center', padding: '32px 20px', opacity: 0.7 }}>
      <i className="ri-toggle-line" style={{ fontSize: 28, color: 'var(--accent-green)', display: 'block', marginBottom: 8 }} />
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
        좌측 <b>레이어 제어</b>에서<br />분석할 레이어를 켜주세요
      </div>
    </div>
  );
}

const SAMPLE_EVENTS = [
  { time: '08:32', text: '성수역 교차로 보행자 밀집', severity: 'high' as const },
  { time: '09:15', text: '뚝섬로 V/C 1.0 초과', severity: 'high' as const },
  { time: '12:40', text: '서울숲 주변 자전거 충돌 위험', severity: 'mid' as const },
  { time: '14:22', text: '성수이로 공사구간 우회', severity: 'low' as const },
  { time: '17:55', text: '왕십리로 출근시간 혼잡 시작', severity: 'mid' as const },
];
