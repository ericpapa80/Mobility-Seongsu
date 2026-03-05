import type { LayerVisibility, StoreMode } from './Sidebar';
import './MapOverlays.css';

interface Props {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  layerVisibility: LayerVisibility;
  storeMode?: StoreMode;
}

export default function MapOverlays({ searchQuery, onSearchChange, layerVisibility, storeMode = 'point' }: Props) {
  const showSpeedLegend = layerVisibility.traffic;

  return (
    <>
      {/* Search Bar */}
      <div className="map-search">
        <i className="ri-search-line" />
        <input
          type="text"
          placeholder="정류장·도로·지역 검색..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>

      {/* Info Chips */}
      <div className="map-info-chips">
        <div className="info-chip">
          <span className="chip-dot live" />
          실시간 데이터
        </div>
        <div className="info-chip">
          <i className="ri-compass-3-line" />
          성수 클러스터
        </div>
      </div>

      {/* Layer Legends — 켜진 레이어에 따라 표시 */}
      <div className="map-legends">
        {layerVisibility.bus && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">버스 정류장 승하차</div>
            <div className="legend-row">
              <span className="legend-label">크기</span>
              <span className="legend-desc">총 승하차 인원</span>
            </div>
            <div className="legend-row legend-colors">
              <span className="legend-swatch" style={{ background: '#06b6d4' }} title="승차 위주" />
              <span className="legend-swatch" style={{ background: '#3b82f6' }} title="균형" />
              <span className="legend-swatch" style={{ background: '#ec4899' }} title="하차 위주" />
            </div>
            <div className="legend-bar-labels">
              <span>승차↑</span>
              <span>균형</span>
              <span>하차↑</span>
            </div>
          </div>
        )}

        {showSpeedLegend && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">교통 속도</div>
            <div className="legend-bar">
              <span className="lb-item" style={{ background: '#10b981' }} />
              <span className="lb-item" style={{ background: '#f59e0b' }} />
              <span className="lb-item" style={{ background: '#ef4444' }} />
              <span className="lb-item" style={{ background: '#991b1b' }} />
            </div>
            <div className="legend-bar-labels">
              <span>고속</span>
              <span>보통</span>
              <span>저속</span>
              <span>정체</span>
            </div>
          </div>
        )}

        {layerVisibility.subway && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">지하철 승하차</div>
            <div className="legend-row">
              <span className="legend-label">크기</span>
              <span className="legend-desc">승하차 인원</span>
            </div>
            <div className="legend-row">
              <span className="legend-label">색상</span>
              <span className="legend-desc">밀도(진할수록 많음)</span>
            </div>
          </div>
        )}

        {layerVisibility.risk && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">위험 구간</div>
            <div className="legend-row legend-colors">
              <span className="legend-swatch risk" style={{ background: '#ef4444' }} />
              <span className="legend-swatch risk" style={{ background: '#f59e0b' }} />
            </div>
            <div className="legend-bar-labels">
              <span>위험</span>
              <span>주의</span>
            </div>
          </div>
        )}

        {layerVisibility.bike && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">공유 자전거</div>
            <div className="legend-row">
              <span className="legend-desc">대여·반납 현황</span>
            </div>
          </div>
        )}

        {layerVisibility.foottraffic && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">보행자 통행량</div>
            <div className="legend-bar">
              <span className="lb-item" style={{ background: '#00681c' }} />
              <span className="lb-item" style={{ background: '#31a354' }} />
              <span className="lb-item" style={{ background: '#ffff00' }} />
              <span className="lb-item" style={{ background: '#ff7f00' }} />
              <span className="lb-item" style={{ background: '#ff0000' }} />
            </div>
            <div className="legend-bar-labels">
              <span>적음</span>
              <span>보통</span>
              <span>많음</span>
            </div>
          </div>
        )}

        {layerVisibility.store && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">상가 분포 <span className="legend-meta">(2025.10)</span></div>
            {(storeMode === 'density' || storeMode === 'both') && (
              <>
                <div className="legend-gradient-bar store-density" />
                <div className="legend-bar-labels">
                  <span>적음</span>
                  <span>보통</span>
                  <span>많음</span>
                </div>
              </>
            )}
            {(storeMode === 'point' || storeMode === 'both') && (
              <>
                <div className="legend-row legend-colors">
                  <span className="legend-swatch" style={{ background: '#fb923c' }} title="음식" />
                  <span className="legend-swatch" style={{ background: '#3b82f6' }} title="소매" />
                  <span className="legend-swatch" style={{ background: '#f472b6' }} title="서비스" />
                </div>
                <div className="legend-bar-labels">
                  <span>음식</span>
                  <span>소매</span>
                  <span>서비스</span>
                </div>
              </>
            )}
          </div>
        )}

        {layerVisibility.building && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">건물 3D</div>
            <div className="legend-row legend-colors">
              <span className="legend-swatch" style={{ background: '#94a3b8' }} title="1~3층" />
              <span className="legend-swatch" style={{ background: '#3b82f6' }} title="4~10층" />
              <span className="legend-swatch" style={{ background: '#8b5cf6' }} title="10층+" />
            </div>
            <div className="legend-bar-labels">
              <span>저층</span>
              <span>중층</span>
              <span>고층</span>
            </div>
          </div>
        )}

        {layerVisibility.salary && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">사업장/급여</div>
            <div className="legend-row">
              <span className="legend-label">크기</span>
              <span className="legend-desc">종업원 수</span>
            </div>
            <div className="legend-row">
              <span className="legend-label">색상</span>
              <span className="legend-desc">업종 구분</span>
            </div>
          </div>
        )}

        {layerVisibility.krafton && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">크래프톤 클러스터</div>
            <div className="legend-row">
              <span className="legend-swatch" style={{ background: 'rgba(236,72,153,0.4)', border: '2px solid #ec4899' }} />
              <span className="legend-desc">클러스터 경계</span>
            </div>
          </div>
        )}

        {layerVisibility.commercialArea && (
          <div className="map-legend-card">
            <div className="legend-overlay-title">상권 경계</div>
            <div className="legend-row">
              <span className="legend-swatch" style={{ background: 'rgba(6,182,212,0.25)', border: '2px solid #06b6d4' }} />
              <span className="legend-desc">상권 영역</span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
