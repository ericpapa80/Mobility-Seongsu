import { useState, useCallback, useEffect } from 'react';
import type { ViewTab } from '../components/Header';
import type { LayerVisibility, FoottrafficSettings, StoreSettings, TrafficMode } from '../components/Sidebar';
import type { DrillState } from '../components/StoreDrillChart';
import { DEFAULT_FT_SETTINGS, DEFAULT_STORE_SETTINGS } from '../components/Sidebar';
import Sidebar from '../components/Sidebar';
import DeckMap from '../components/DeckMap';
import TimeSlider from '../components/TimeSlider';
import MapOverlays from '../components/MapOverlays';
import RightPanel from '../components/RightPanel';
import StopDetailPanel from '../components/StopDetailPanel';
import StoreDetailPanel from '../components/StoreDetailPanel';
import DownloadModal from '../components/DownloadModal';
import AdminModal from '../components/AdminModal';
import SourcesModal from '../components/SourcesModal';
import {
  useBusStopsHourly,
  useBusStopsHourlyFull,
  useSubwayStations,
  useSubwayEntrances,
  useSubwayPolygons,
  useSubwayHourly,
  useRiskPoints,
  useTraffic,
  useTrafficPattern,
  useTrafficRealtime,
  useFoottraffic,
  useStores,
  useBuildings,
  useSalary,
  useKraftonCluster,
  useCommercialArea,
} from '../hooks/useMapData';
import type { BusStopHourly, Store } from '../api/client';
import './Dashboard.css';

const STORAGE_KEY_LAYERS = 'ms_layers';
const DEFAULT_LAYERS: LayerVisibility = {
  bus: false, traffic: false,
  subway: false, risk: false, bike: false,
  store: false, building: false, salary: false, foottraffic: false,
  krafton: false, commercialArea: false, commercialAreaLabel: true, commercialAreaChart: false,
};

function loadLayers(): LayerVisibility {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_LAYERS);
    if (!raw) return DEFAULT_LAYERS;
    const parsed = JSON.parse(raw);
    const result = { ...DEFAULT_LAYERS };
    for (const k of Object.keys(DEFAULT_LAYERS) as (keyof LayerVisibility)[]) {
      if (typeof parsed[k] === 'boolean') result[k] = parsed[k];
    }
    return result;
  } catch {
    return DEFAULT_LAYERS;
  }
}

interface Props {
  activeView: ViewTab;
  showDownload: boolean;
  showAdmin: boolean;
  showSources: boolean;
  onCloseDownload: () => void;
  onCloseAdmin: () => void;
  onCloseSources: () => void;
}

export default function Dashboard({ activeView, showDownload, showAdmin, showSources, onCloseDownload, onCloseAdmin, onCloseSources }: Props) {
  const [hour, setHour] = useState(8);
  const [searchQuery, setSearchQuery] = useState('');
  const [rightCollapsed, setRightCollapsed] = useState(false);
  const [rightExpanded, setRightExpanded] = useState(false);
  const [focusMode, setFocusMode] = useState(false);

  const [layers, setLayers] = useState<LayerVisibility>(loadLayers);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_LAYERS, JSON.stringify(layers));
  }, [layers]);

  const [ftSettings, setFtSettings] = useState<FoottrafficSettings>(DEFAULT_FT_SETTINGS);
  const [storeSettings, setStoreSettings] = useState<StoreSettings>(DEFAULT_STORE_SETTINGS);
  const [selectedStop, setSelectedStop] = useState<{ id: number; name: string } | null>(null);
  const [trafficMode, setTrafficMode] = useState<TrafficMode>('pattern');

  const { data: busData } = useBusStopsHourly(hour);
  const { data: busFullData } = useBusStopsHourlyFull();
  const { data: subwayData } = useSubwayStations();
  const { data: entranceData } = useSubwayEntrances();
  const { data: polygonData } = useSubwayPolygons();
  const { data: subwayHourlyData } = useSubwayHourly();
  const { data: riskData } = useRiskPoints();
  const { data: trafficData } = useTraffic();
  const { data: trafficPatternData } = useTrafficPattern();
  const { data: trafficRealtimeData } = useTrafficRealtime(layers.traffic && trafficMode === 'realtime');
  const { data: foottrafficData } = useFoottraffic();
  const { data: storesData } = useStores();
  const { data: buildingsData } = useBuildings();
  const { data: salaryData } = useSalary();
  const { data: kraftonData } = useKraftonCluster();
  const { data: commercialAreaData } = useCommercialArea();

  const [selectedStore, setSelectedStore] = useState<Store | null>(null);
  const [drillState, setDrillState] = useState<DrillState>({ level: 'all' });

  const handleDrillStateChange = useCallback((state: DrillState) => {
    setDrillState(state);
  }, []);

  const toggleLayer = useCallback((key: keyof LayerVisibility) => {
    setLayers(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleStopClick = useCallback((stop: BusStopHourly) => {
    setSelectedStop({ id: stop.id, name: stop.name });
  }, []);

  const handleHourChange = useCallback((val: number | ((prev: number) => number)) => {
    setHour(typeof val === 'function' ? val : val);
  }, []);

  return (
    <>
      <div className={`dashboard${focusMode ? ' focus-mode' : ''}`}>
        {!focusMode && (
        <Sidebar layers={layers} onToggle={toggleLayer} activeView={activeView}
          foottrafficSettings={ftSettings} onFoottrafficSettings={setFtSettings}
          storeSettings={storeSettings} onStoreSettings={setStoreSettings}
          trafficMode={trafficMode} onTrafficModeChange={setTrafficMode}
          trafficRealtimeTime={trafficRealtimeData?.meta?.fetched_at ?? null} />
        )}

        <div className="dashboard-main">
          <div className="map-area">
            <DeckMap
              hour={hour}
              busStops={busData?.stops ?? []}
              subwayStations={subwayData?.stations ?? []}
              subwayEntrances={entranceData?.entrances ?? []}
              subwayPolygons={polygonData ?? null}
              subwayHourlyStations={subwayHourlyData?.stations ?? []}
              riskPoints={riskData?.points ?? []}
              trafficSegments={trafficData?.segments ?? []}
              trafficRealtimeSegments={trafficRealtimeData?.segments ?? []}
              trafficMode={trafficMode}
              foottrafficData={foottrafficData ?? null}
              foottrafficSettings={ftSettings}
              stores={storesData?.stores ?? []}
              storeSettings={storeSettings}
              buildingsGeoJson={buildingsData ?? null}
              salaryWorkplaces={salaryData?.workplaces ?? []}
              kraftonGeoJson={kraftonData ?? null}
              commercialAreaGeoJson={commercialAreaData ?? null}
              layerVisibility={layers}
              busStopsFull={busFullData?.stops ?? []}
              onStopClick={handleStopClick}
              onStoreClick={setSelectedStore}
              drillState={drillState}
            />
            <MapOverlays searchQuery={searchQuery} onSearchChange={setSearchQuery} layerVisibility={layers} storeMode={storeSettings.mode} focusMode={focusMode} onFocusToggle={() => setFocusMode(f => !f)} />
            <TimeSlider hour={hour} onChange={handleHourChange} trafficMode={trafficMode} trafficLayerOn={layers.traffic} />
          </div>
        </div>

        {!focusMode && (
        <RightPanel
          activeView={activeView}
          busStops={busData?.stops ?? []}
          busStopsFull={busFullData?.stops ?? []}
          subwayHourlyStations={subwayHourlyData?.stations ?? []}
          trafficSegments={trafficData?.segments ?? []}
          foottrafficData={foottrafficData ?? null}
          stores={storesData?.stores ?? []}
          storeSettings={storeSettings}
          salaryData={salaryData ?? null}
          commercialAreaGeoJson={commercialAreaData ?? null}
          layerVisibility={layers}
          foottrafficSettings={ftSettings}
          currentHour={hour}
          collapsed={rightCollapsed}
          onToggle={() => setRightCollapsed(c => !c)}
          expanded={rightExpanded}
          onExpandToggle={() => setRightExpanded(e => !e)}
          onDrillStateChange={handleDrillStateChange}
          trafficMode={trafficMode}
          trafficRealtimeSegments={trafficRealtimeData?.segments ?? []}
          trafficPatternData={trafficPatternData ?? null}
        />
        )}

        {selectedStop && (
          <StopDetailPanel
            stopId={selectedStop.id}
            stopName={selectedStop.name}
            onClose={() => setSelectedStop(null)}
          />
        )}

        {selectedStore && (
          <StoreDetailPanel
            store={selectedStore}
            onClose={() => setSelectedStore(null)}
          />
        )}
      </div>

      <DownloadModal open={showDownload} onClose={onCloseDownload} />
      <AdminModal open={showAdmin} onClose={onCloseAdmin} />
      <SourcesModal open={showSources} onClose={onCloseSources} />
    </>
  );
}
