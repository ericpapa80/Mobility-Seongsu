import { useState, useCallback, useMemo, forwardRef, useImperativeHandle } from 'react';
import { Map as MapGL } from 'react-map-gl/maplibre';
import DeckGL from '@deck.gl/react';
import { ScatterplotLayer, PathLayer, TextLayer, GeoJsonLayer } from '@deck.gl/layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import type { MapViewState, PickingInfo } from '@deck.gl/core';
import type {
  BusStopHourly, BusStopHourlyFull, SubwayStation, SubwayEntrance,
  RiskPoint, GeoJSONCollection, SubwayStationHourly,
  TrafficSegment, TrafficRealtimeSegment, FoottrafficLink, FoottrafficResponse, Store, Workplace,
  GeoJSONFeature,
} from '../api/client';
import type { LayerVisibility, FoottrafficSettings, StoreSettings, TrafficMode } from './Sidebar';
import { busMarkerColor, busMarkerRadius } from '../lib/colors';
import {
  speedColor, gradeColor, storeCategoryColor, buildingColor, industryColor,
  HOUR_TO_TMZON, HOUR_TO_STORE_SLOT, HEATMAP_COLOR_RANGE, STORE_HEATMAP_RANGE,
} from '../lib/layer_colors';
import { extractAreas, polygonCentroid } from '../lib/geo';
import MiniAreaChart from './MiniAreaChart';
import type { DrillState } from './StoreDrillChart';

const INITIAL_VIEW: MapViewState = {
  longitude: 127.056,
  latitude: 37.5445,
  zoom: 14.5,
  pitch: 0,
  bearing: 0,
};

const BASEMAP = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

const ZOOM_EXIT_THRESHOLD = 15.5;

interface Props {
  hour: number;
  busStops: BusStopHourly[];
  subwayStations: SubwayStation[];
  subwayEntrances: SubwayEntrance[];
  subwayPolygons: GeoJSONCollection | null;
  subwayHourlyStations: SubwayStationHourly[];
  riskPoints: RiskPoint[];
  trafficSegments: TrafficSegment[];
  trafficRealtimeSegments?: TrafficRealtimeSegment[];
  trafficMode?: TrafficMode;
  foottrafficData: FoottrafficResponse | null;
  foottrafficSettings: FoottrafficSettings;
  stores: Store[];
  storeSettings: StoreSettings;
  buildingsGeoJson: GeoJSONCollection | null;
  salaryWorkplaces: Workplace[];
  kraftonGeoJson: GeoJSONCollection | null;
  commercialAreaGeoJson: GeoJSONCollection | null;
  layerVisibility: LayerVisibility;
  busStopsFull: BusStopHourlyFull[];
  onStopClick?: (stop: BusStopHourly) => void;
  onStoreClick?: (store: Store) => void;
  drillState?: DrillState;
}

export interface DeckMapRef {
  resetView: () => void;
}

const DeckMapInner = forwardRef<DeckMapRef, Props>(function DeckMapInner({
  hour, busStops,
  subwayStations, subwayEntrances, subwayPolygons,
  subwayHourlyStations, riskPoints,
  trafficSegments, trafficRealtimeSegments = [], trafficMode = 'pattern',
  foottrafficData, foottrafficSettings, stores, storeSettings,
  buildingsGeoJson, salaryWorkplaces, kraftonGeoJson, commercialAreaGeoJson,
  layerVisibility, busStopsFull, onStopClick, onStoreClick, drillState,
}, ref) {
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW);

  useImperativeHandle(ref, () => ({
    resetView: () => setViewState(INITIAL_VIEW),
  }), []);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  const isZoomedIn = viewState.zoom >= ZOOM_EXIT_THRESHOLD;
  const currentTmzon = HOUR_TO_TMZON[hour] ?? '06~10';

  const exitTrafficLookup = useMemo(() => {
    const map = new Map<string, number[]>();
    for (const stn of subwayHourlyStations) {
      for (const [exitNo, hourly] of Object.entries(stn.exit_traffic.by_exit)) {
        map.set(`${stn.name}_${exitNo}`, hourly);
      }
    }
    return map;
  }, [subwayHourlyStations]);

  const roadLabels = useMemo(() => {
    if (!layerVisibility.traffic || trafficMode !== 'pattern' || trafficSegments.length === 0) return [];

    const halfLng = 900 / (256 * Math.pow(2, viewState.zoom)) * 360 / 2;
    const halfLat = 600 / (256 * Math.pow(2, viewState.zoom)) * 360 / 2;
    const vMinLng = viewState.longitude - halfLng;
    const vMaxLng = viewState.longitude + halfLng;
    const vMinLat = viewState.latitude - halfLat;
    const vMaxLat = viewState.latitude + halfLat;

    const inView = (c: number[]) =>
      c[0] >= vMinLng && c[0] <= vMaxLng && c[1] >= vMinLat && c[1] <= vMaxLat;

    const grouped = new Map<string, TrafficSegment[]>();
    for (const s of trafficSegments) {
      if (!s.road_name) continue;
      const list = grouped.get(s.road_name) ?? [];
      list.push(s);
      grouped.set(s.road_name, list);
    }

    const labels: { position: [number, number]; text: string; angle: number }[] = [];

    for (const [name, segs] of grouped) {
      let bestCoords: number[][] = [];

      for (const seg of segs) {
        const coords = seg.coordinates;
        const visIdx: number[] = [];
        for (let i = 0; i < coords.length; i++) {
          if (inView(coords[i])) visIdx.push(i);
        }
        if (visIdx.length < 2) continue;

        let longestStart = 0, longestLen = 1, curStart = 0, curLen = 1;
        for (let k = 1; k < visIdx.length; k++) {
          if (visIdx[k] === visIdx[k - 1] + 1) {
            curLen++;
          } else {
            curStart = k;
            curLen = 1;
          }
          if (curLen > longestLen) {
            longestLen = curLen;
            longestStart = curStart;
          }
        }

        const run = visIdx.slice(longestStart, longestStart + longestLen).map(i => coords[i]);
        if (run.length > bestCoords.length) bestCoords = run;
      }
      if (bestCoords.length < 2) continue;

      const midIdx = Math.floor(bestCoords.length / 2);
      const mid = bestCoords[midIdx];

      const span = Math.max(1, Math.floor(bestCoords.length * 0.15));
      const pA = bestCoords[Math.max(0, midIdx - span)];
      const pB = bestCoords[Math.min(bestCoords.length - 1, midIdx + span)];

      const cosLat = Math.cos(mid[1] * Math.PI / 180);
      const dx = (pB[0] - pA[0]) * cosLat;
      const dy = pB[1] - pA[1];
      let angleDeg = Math.atan2(dy, dx) * (180 / Math.PI);
      if (angleDeg > 90) angleDeg -= 180;
      if (angleDeg < -90) angleDeg += 180;

      labels.push({ position: [mid[0], mid[1]], text: name, angle: angleDeg });
    }
    return labels;
  }, [trafficSegments, layerVisibility.traffic, trafficMode, viewState.longitude, viewState.latitude, viewState.zoom]);

  const commercialAreaLabels = useMemo(() => {
    if (!commercialAreaGeoJson) return [];
    return commercialAreaGeoJson.features.map(f => {
      const ring = (f.geometry.coordinates as number[][][][])[0][0];
      const centroid = polygonCentroid(ring);
      return { position: centroid, name: f.properties['상권명'] as string };
    });
  }, [commercialAreaGeoJson]);

  const commercialAreaDefs = useMemo(() => {
    if (!commercialAreaGeoJson) return [];
    return extractAreas(commercialAreaGeoJson);
  }, [commercialAreaGeoJson]);

  const handleHover = useCallback((info: PickingInfo) => {
    if (info.object && info.layer) {
      const obj = info.object as Record<string, unknown>;
      const layerId = info.layer.id;

      if (layerId === 'subway-entrances' || layerId === 'subway-entrance-traffic') {
        const ent = obj as unknown as SubwayEntrance;
        const hourly = exitTrafficLookup.get(`${ent.station_name}_${ent.entrance_no}`);
        const count = hourly ? hourly[hour] ?? 0 : 0;
        const text = `${ent.station_name} ${ent.entrance_no}번 출구  |  ${count.toLocaleString()}명`;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text });
      } else if (layerId === 'subway-station-traffic' || layerId === 'subway-stations') {
        const stn = obj as unknown as SubwayStationHourly;
        const ride = stn.ridership?.ride?.[hour] ?? 0;
        const alight = stn.ridership?.alight?.[hour] ?? 0;
        const text = `${stn.name}  |  승차 ${ride.toLocaleString()} · 하차 ${alight.toLocaleString()}`;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text });
      } else if (layerId === 'bus-stops') {
        const stop = obj as unknown as BusStopHourly;
        const ride = stop.ride ?? 0;
        const alight = stop.alight ?? 0;
        const text = `${stop.name}\n승차 ${ride.toLocaleString()}명 · 하차 ${alight.toLocaleString()}명`;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text });
      } else if (layerId === 'traffic-speed') {
        const seg = obj as unknown as TrafficSegment;
        const spd = seg.speeds[hour] ?? 0;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `${seg.road_name || '도로'} ${seg.direction}\n속도: ${spd} km/h  |  차선: ${seg.lanes}` });
      } else if (layerId === 'traffic-speed-realtime') {
        const seg = obj as unknown as TrafficRealtimeSegment;
        const trvMin = Math.floor(seg.travel_time / 60);
        const trvSec = Math.round(seg.travel_time % 60);
        const trvText = trvMin > 0 ? `${trvMin}분 ${trvSec}초` : `${trvSec}초`;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `${seg.road_name || '도로'} ${seg.direction}\n실시간 속도: ${seg.speed} km/h  |  차선: ${seg.lanes}\n통과시간: ${trvText}` });
      } else if (layerId === 'foottraffic-paths') {
        const link = obj as unknown as FoottrafficLink;
        const tz = link.data?.[foottrafficSettings.dayweek]?.[foottrafficSettings.agrde]?.[currentTmzon];
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `보행 링크 ${link.road_link_id}\n통행량: ${tz?.acost ?? 0}  |  등급: ${tz?.grade ?? '-'}  |  혼잡: ${tz?.per ?? 0}%` });
      } else if (layerId === 'stores') {
        const s = obj as unknown as Store;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `${s.name}\n${s.category_bg} > ${s.category_mi}\n추정매출: ${s.peco_total.toLocaleString()}만원` });
      } else if (layerId === 'salary-workplaces') {
        const w = obj as unknown as Workplace;
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `${w.name}\n${w.industry}\n종업원: ${w.employees}명  |  월급여: ${w.monthly_salary.toLocaleString()}원` });
      } else if (layerId === 'buildings-3d') {
        const p = (obj as { properties?: Record<string, unknown> }).properties ?? {};
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `${p.buld_nm || '건물'}\n지상 ${p.gro_flo_co ?? '?'}층  |  ${p.rd_nm || ''}` });
      } else if (layerId === 'krafton-cluster') {
        const p = (obj as { properties?: Record<string, unknown> }).properties ?? {};
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `${p.jibun || ''}\n지목: ${p.jimok || '-'}  |  면적: ${p.parea || '-'}㎡` });
      } else if (layerId === 'commercial-area') {
        const p = (obj as { properties?: Record<string, unknown> }).properties ?? {};
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: `상권: ${p['상권명'] || '-'}` });
      } else {
        const name = (obj.name as string) ?? '';
        setTooltip({ x: info.x ?? 0, y: info.y ?? 0, text: name });
      }
    } else {
      setTooltip(null);
    }
  }, [exitTrafficLookup, hour, currentTmzon]);

  const layers = [
    // ── Commercial Area GeoJsonLayer (가장 뒤) ──
    layerVisibility.commercialArea && commercialAreaGeoJson && new GeoJsonLayer({
      id: 'commercial-area',
      data: commercialAreaGeoJson,
      getFillColor: [6, 182, 212, 30] as [number, number, number, number],
      getLineColor: [6, 182, 212, 180] as [number, number, number, number],
      lineWidthMinPixels: 2,
      pickable: true,
    }),

    layerVisibility.subway && subwayPolygons && new GeoJsonLayer({
      id: 'subway-polygons',
      data: subwayPolygons,
      getFillColor: [16, 185, 129, 40] as [number, number, number, number],
      getLineColor: [16, 185, 129, 120] as [number, number, number, number],
      lineWidthMinPixels: 1,
      pickable: true,
    }),

    /* ── 줌아웃: 역사별 합계 ── */
    layerVisibility.subway && !isZoomedIn && new ScatterplotLayer({
      id: 'subway-station-traffic',
      data: subwayHourlyStations,
      getPosition: (d: SubwayStationHourly) => [d.lng, d.lat],
      getRadius: (d: SubwayStationHourly) => {
        const total = d.ridership.ride[hour] + d.ridership.alight[hour];
        return Math.max(25, Math.sqrt(total) * 0.8);
      },
      radiusUnits: 'meters' as const,
      getFillColor: [16, 185, 129, 100] as [number, number, number, number],
      getLineColor: [16, 185, 129, 220] as [number, number, number, number],
      lineWidthMinPixels: 2,
      stroked: true,
      pickable: true,
      updateTriggers: { getRadius: hour },
    }),

    layerVisibility.subway && !isZoomedIn && new ScatterplotLayer({
      id: 'subway-stations',
      data: subwayStations,
      getPosition: (d: SubwayStation) => [d.lng, d.lat],
      getRadius: 18,
      radiusUnits: 'meters' as const,
      getFillColor: [16, 185, 129, 220] as [number, number, number, number],
      getLineColor: [255, 255, 255, 200] as [number, number, number, number],
      lineWidthMinPixels: 2,
      stroked: true,
      pickable: true,
    }),

    layerVisibility.subway && !isZoomedIn && new TextLayer({
      id: 'subway-labels',
      data: subwayHourlyStations,
      getPosition: (d: SubwayStationHourly) => [d.lng, d.lat],
      getText: (d: SubwayStationHourly) => d.name,
      getSize: 13,
      getColor: [16, 185, 129, 255],
      getPixelOffset: [0, -28],
      fontFamily: 'Pretendard, sans-serif',
      fontWeight: 700,
      characterSet: 'auto',
    }),

    layerVisibility.subway && !isZoomedIn && new TextLayer({
      id: 'subway-station-count',
      data: subwayHourlyStations,
      getPosition: (d: SubwayStationHourly) => [d.lng, d.lat],
      getText: (d: SubwayStationHourly) => {
        const total = d.ridership.ride[hour] + d.ridership.alight[hour];
        return total.toLocaleString() + '명';
      },
      getSize: 11,
      getColor: [255, 255, 255, 210],
      getPixelOffset: [0, -14],
      fontFamily: "'JetBrains Mono', 'Pretendard', monospace",
      fontWeight: 600,
      characterSet: 'auto',
      updateTriggers: { getText: hour },
    }),

    /* ── 줌인: 출구별 상세 ── */
    layerVisibility.subway && isZoomedIn && new ScatterplotLayer({
      id: 'subway-entrance-traffic',
      data: subwayEntrances,
      getPosition: (d: SubwayEntrance) => [d.lng, d.lat],
      getRadius: (d: SubwayEntrance) => {
        const hourly = exitTrafficLookup.get(`${d.station_name}_${d.entrance_no}`);
        const count = hourly ? hourly[hour] ?? 0 : 0;
        return Math.max(6, Math.sqrt(count) * 1.2);
      },
      radiusUnits: 'meters' as const,
      radiusMinPixels: 4,
      getFillColor: (d: SubwayEntrance) => {
        const hourly = exitTrafficLookup.get(`${d.station_name}_${d.entrance_no}`);
        const count = hourly ? hourly[hour] ?? 0 : 0;
        const intensity = Math.min(count / 800, 1);
        return [0, 255, 136, 20 + intensity * 110] as [number, number, number, number];
      },
      getLineColor: (d: SubwayEntrance) => {
        const hourly = exitTrafficLookup.get(`${d.station_name}_${d.entrance_no}`);
        const count = hourly ? hourly[hour] ?? 0 : 0;
        const intensity = Math.min(count / 800, 1);
        return [0, 255, 136, 60 + intensity * 160] as [number, number, number, number];
      },
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      updateTriggers: {
        getRadius: hour,
        getFillColor: hour,
        getLineColor: hour,
      },
    }),

    layerVisibility.subway && isZoomedIn && new ScatterplotLayer({
      id: 'subway-entrances',
      data: subwayEntrances,
      getPosition: (d: SubwayEntrance) => [d.lng, d.lat],
      getRadius: 6,
      radiusUnits: 'pixels' as const,
      getFillColor: [0, 255, 136, 200] as [number, number, number, number],
      getLineColor: [255, 255, 255, 180] as [number, number, number, number],
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
    }),

    layerVisibility.subway && isZoomedIn && new TextLayer({
      id: 'subway-entrance-labels',
      data: subwayEntrances,
      getPosition: (d: SubwayEntrance) => [d.lng, d.lat],
      getText: (d: SubwayEntrance) => String(d.entrance_no),
      getSize: 12,
      sizeUnits: 'pixels' as const,
      getColor: [12, 12, 12, 255],
      getPixelOffset: [0, -14],
      fontFamily: 'Space Grotesk, sans-serif',
      fontWeight: 700,
      getTextAnchor: 'middle' as const,
      getAlignmentBaseline: 'bottom' as const,
      background: true,
      getBackgroundColor: [0, 255, 136, 220] as [number, number, number, number],
      backgroundPadding: [3, 1, 3, 1] as [number, number, number, number],
      getBorderColor: [0, 0, 0, 0] as [number, number, number, number],
      getBorderWidth: 0,
    }),

    layerVisibility.risk && new ScatterplotLayer({
      id: 'risk-points',
      data: riskPoints,
      getPosition: (d: RiskPoint) => [d.lng, d.lat],
      getRadius: 40,
      radiusUnits: 'meters' as const,
      getFillColor: (d: RiskPoint) =>
        d.risk === 'high'
          ? [239, 68, 68, 200] as [number, number, number, number]
          : [245, 158, 11, 200] as [number, number, number, number],
      getLineColor: [255, 255, 255, 200] as [number, number, number, number],
      lineWidthMinPixels: 2,
      stroked: true,
      pickable: true,
    }),

    layerVisibility.bus && new ScatterplotLayer({
      id: 'bus-stops',
      data: busStops,
      getPosition: (d: BusStopHourly) => [d.lng, d.lat],
      getRadius: (d: BusStopHourly) => busMarkerRadius(d.ride + d.alight, hour),
      radiusUnits: 'meters' as const,
      getFillColor: (d: BusStopHourly) => busMarkerColor(d.ride, d.alight),
      getLineColor: [255, 255, 255, 180] as [number, number, number, number],
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
      onClick: (info: PickingInfo<BusStopHourly>) => {
        if (info.object && onStopClick) onStopClick(info.object);
      },
    }),

    // ── Traffic Speed Layer (pattern mode) ──
    layerVisibility.traffic && trafficMode === 'pattern' && trafficSegments.length > 0 && new PathLayer<TrafficSegment>({
      id: 'traffic-speed',
      data: trafficSegments,
      getPath: (d) => d.coordinates,
      getColor: (d) => speedColor(d.speeds[hour] ?? 0),
      getWidth: (d) => Math.max(2, d.lanes * 2),
      widthUnits: 'pixels' as const,
      capRounded: true,
      pickable: true,
      updateTriggers: { getColor: [hour] },
    }),

    // ── Traffic Speed Layer (realtime mode) ──
    layerVisibility.traffic && trafficMode === 'realtime' && trafficRealtimeSegments.length > 0 && new PathLayer<TrafficRealtimeSegment>({
      id: 'traffic-speed-realtime',
      data: trafficRealtimeSegments,
      getPath: (d) => d.coordinates,
      getColor: (d) => speedColor(d.speed),
      getWidth: (d) => Math.max(2, d.lanes * 2),
      widthUnits: 'pixels' as const,
      capRounded: true,
      pickable: true,
    }),

    // ── Traffic Road Name Labels ──
    layerVisibility.traffic && roadLabels.length > 0 && new TextLayer({
      id: 'traffic-road-labels',
      data: roadLabels,
      getPosition: (d: { position: [number, number] }) => d.position,
      getText: (d: { text: string }) => d.text,
      getAngle: (d: { angle: number }) => d.angle,
      getSize: 10.5,
      getColor: [230, 230, 230, 255],
      fontFamily: 'Pretendard, sans-serif',
      fontWeight: 600,
      characterSet: 'auto',
      fontSettings: { sdf: true, buffer: 6, radius: 12 },
      outlineWidth: 2,
      outlineColor: [0, 0, 0, 200],
    }),

    // ── Foottraffic HeatmapLayer ──
    layerVisibility.foottraffic && foottrafficData
      && (foottrafficSettings.mode === 'density' || foottrafficSettings.mode === 'both')
      && new HeatmapLayer<FoottrafficLink>({
      id: 'foottraffic-density',
      data: foottrafficData.links,
      getPosition: (d) => d.centroid as [number, number],
      getWeight: (d) =>
        d.data?.[foottrafficSettings.dayweek]?.[foottrafficSettings.agrde]?.[currentTmzon]?.[foottrafficSettings.metric] ?? 0,
      radiusPixels: foottrafficSettings.radius,
      intensity: foottrafficSettings.intensity,
      threshold: 0.03,
      opacity: foottrafficSettings.mode === 'both' ? foottrafficSettings.opacity * 0.7 : foottrafficSettings.opacity,
      colorDomain: [0, (() => {
        const m = foottrafficSettings.metric;
        const dimKey = `${foottrafficSettings.dayweek}_${foottrafficSettings.agrde}`;
        const maxKey = `${m === 'cost' ? 'cost' : 'acost'}_${currentTmzon}`;
        if (m === 'grade') return 5;
        if (m === 'per') return 100;
        return foottrafficData.meta.max_vals?.[dimKey]?.[maxKey] || 1000;
      })()],
      colorRange: HEATMAP_COLOR_RANGE,
      updateTriggers: {
        getWeight: [currentTmzon, foottrafficSettings.metric, foottrafficSettings.dayweek, foottrafficSettings.agrde],
      },
    }),

    // ── Foottraffic PathLayer ──
    layerVisibility.foottraffic && foottrafficData
      && (foottrafficSettings.mode === 'polyline' || (foottrafficSettings.mode === 'both' && isZoomedIn))
      && new PathLayer<FoottrafficLink>({
      id: 'foottraffic-paths',
      data: foottrafficData.links,
      getPath: (d) => d.coordinates,
      getColor: (d) =>
        gradeColor(d.data?.[foottrafficSettings.dayweek]?.[foottrafficSettings.agrde]?.[currentTmzon]?.grade ?? 1),
      getWidth: (d) => {
        const v = d.data?.[foottrafficSettings.dayweek]?.[foottrafficSettings.agrde]?.[currentTmzon]?.[foottrafficSettings.metric] ?? 0;
        if (foottrafficSettings.metric === 'grade') return Math.max(2, v * 2);
        if (foottrafficSettings.metric === 'per') return Math.max(2, v / 8);
        return Math.max(2, Math.sqrt(v) * 0.3);
      },
      widthMinPixels: 1,
      widthMaxPixels: 12,
      opacity: foottrafficSettings.opacity,
      pickable: true,
      updateTriggers: {
        getColor: [currentTmzon, foottrafficSettings.dayweek, foottrafficSettings.agrde],
        getWidth: [currentTmzon, foottrafficSettings.metric, foottrafficSettings.dayweek, foottrafficSettings.agrde],
      },
    }),

    // ── Store HeatmapLayer ──
    layerVisibility.store
      && (storeSettings.mode === 'density' || storeSettings.mode === 'both')
      && new HeatmapLayer<Store>({
      id: 'store-density',
      data: stores.filter(s => storeSettings.categories.includes(s.category_bg)),
      getPosition: (d) => [d.lng, d.lat] as [number, number],
      getWeight: (d) => {
        const sb = storeSettings.sizeBy;
        if (sb === 'peco_individual') return d.peco_individual;
        if (sb === 'peco_foreign') return d.peco_foreign;
        if (sb === 'time_slot') return d.times[HOUR_TO_STORE_SLOT[hour] ?? '점심'] ?? d.peco_total;
        if (sb === 'demographic' && storeSettings.demographic !== 'all') {
          const [gender, age] = [storeSettings.demographic[0], storeSettings.demographic.slice(2) + '대'];
          return (gender === 'f' ? d.gender_f : d.gender_m)[age] ?? 0;
        }
        return d.peco_total;
      },
      radiusPixels: storeSettings.radius,
      intensity: storeSettings.intensity,
      threshold: 0.03,
      opacity: storeSettings.mode === 'both' ? storeSettings.opacity * 0.7 : storeSettings.opacity,
      colorRange: STORE_HEATMAP_RANGE,
      updateTriggers: {
        getWeight: [storeSettings.sizeBy, hour, storeSettings.demographic],
        data: [storeSettings.categories],
      },
    }),

    // ── Store ScatterplotLayer ──
    layerVisibility.store
      && (storeSettings.mode === 'point' || storeSettings.mode === 'both')
      && new ScatterplotLayer<Store>({
      id: 'stores',
      data: stores.filter(s => storeSettings.categories.includes(s.category_bg)),
      getPosition: (d) => [d.lng, d.lat],
      getRadius: (d) => {
        let v = d.peco_total;
        const sb = storeSettings.sizeBy;
        if (sb === 'peco_individual') v = d.peco_individual;
        else if (sb === 'peco_foreign') v = d.peco_foreign;
        else if (sb === 'time_slot') v = d.times[HOUR_TO_STORE_SLOT[hour] ?? '점심'] ?? d.peco_total;
        else if (sb === 'demographic' && storeSettings.demographic !== 'all') {
          const [gender, age] = [storeSettings.demographic[0], storeSettings.demographic.slice(2) + '대'];
          v = (gender === 'f' ? d.gender_f : d.gender_m)[age] ?? 0;
        }
        return Math.max(8, Math.sqrt(v) * 0.3);
      },
      radiusUnits: 'meters' as const,
      radiusMinPixels: 3,
      getFillColor: (d) => storeCategoryColor(d.category_bg),
      getLineColor: [255, 255, 255, 120] as [number, number, number, number],
      lineWidthMinPixels: 1,
      stroked: true,
      opacity: storeSettings.opacity,
      pickable: true,
      onClick: (info: PickingInfo<Store>) => {
        if (info.object && onStoreClick) onStoreClick(info.object);
      },
      updateTriggers: {
        getRadius: [storeSettings.sizeBy, hour, storeSettings.demographic],
        data: [storeSettings.categories],
      },
    }),

    // ── Building 3D GeoJsonLayer ──
    layerVisibility.building && buildingsGeoJson && new GeoJsonLayer({
      id: 'buildings-3d',
      data: buildingsGeoJson,
      extruded: true,
      wireframe: true,
      getElevation: (d: GeoJSONFeature) => ((d.properties.gro_flo_co as number) || 1) * 3.5,
      getFillColor: (d: GeoJSONFeature) => buildingColor((d.properties.gro_flo_co as number) || 1),
      opacity: 0.6,
      material: { ambient: 0.3, diffuse: 0.6, shininess: 32 },
      pickable: true,
    }),

    // ── Salary/Workplace ScatterplotLayer ──
    layerVisibility.salary && new ScatterplotLayer<Workplace>({
      id: 'salary-workplaces',
      data: salaryWorkplaces,
      getPosition: (d) => [d.lng, d.lat],
      getRadius: (d) => Math.max(10, Math.sqrt(d.employees) * 1.5),
      radiusUnits: 'meters' as const,
      radiusMinPixels: 3,
      getFillColor: (d) => industryColor(d.industry),
      getLineColor: [255, 255, 255, 100] as [number, number, number, number],
      lineWidthMinPixels: 1,
      stroked: true,
      pickable: true,
    }),

    // ── Krafton Cluster GeoJsonLayer ──
    layerVisibility.krafton && kraftonGeoJson && new GeoJsonLayer({
      id: 'krafton-cluster',
      data: kraftonGeoJson,
      getFillColor: [236, 72, 153, 60] as [number, number, number, number],
      getLineColor: [236, 72, 153, 200] as [number, number, number, number],
      lineWidthMinPixels: 2,
      pickable: true,
    }),

    // ── Commercial Area Labels (가장 앞) ──
    layerVisibility.commercialArea && layerVisibility.commercialAreaLabel
      && commercialAreaLabels.length > 0 && new TextLayer({
      id: 'commercial-area-labels',
      data: commercialAreaLabels,
      getPosition: (d: { position: [number, number] }) => d.position,
      getText: (d: { name: string }) => d.name,
      getSize: 13,
      getColor: [6, 182, 212, 255],
      fontFamily: 'Pretendard, sans-serif',
      fontWeight: 700,
      characterSet: 'auto',
      fontSettings: { sdf: true, buffer: 6, radius: 12 },
      outlineWidth: 2.5,
      outlineColor: [0, 0, 0, 220],
      getTextAnchor: 'middle' as const,
      getAlignmentBaseline: 'center' as const,
    }),
  ].filter(Boolean);

  return (
    <div
      style={{ position: 'relative', width: '100%', height: '100%' }}
      onContextMenu={(e) => e.preventDefault()}
    >
      <DeckGL
        viewState={viewState}
        onViewStateChange={(e) => setViewState(e.viewState as MapViewState)}
        controller
        layers={layers}
        onHover={handleHover}
        getTooltip={undefined}
      >
        <MapGL mapStyle={BASEMAP} />
      </DeckGL>

      {layerVisibility.commercialArea && layerVisibility.commercialAreaChart
        && commercialAreaLabels.length > 0 && commercialAreaDefs.length > 0 && (
        <MiniAreaChart
          areas={commercialAreaLabels}
          areaDefs={commercialAreaDefs}
          viewState={viewState}
          layerVisibility={layerVisibility}
          stores={stores}
          storeSettings={storeSettings}
          foottrafficData={foottrafficData}
          foottrafficSettings={foottrafficSettings}
          busStopsFull={busStopsFull}
          drillState={drillState}
        />
      )}

      {tooltip && (
        <div
          style={{
            position: 'absolute',
            left: tooltip.x + 12,
            top: tooltip.y - 30,
            background: '#0C0C0C',
            border: '1px solid rgba(0, 255, 136, 0.35)',
            borderRadius: '2px',
            padding: '6px 10px',
            fontSize: '12px',
            fontFamily: "'JetBrains Mono', 'Pretendard', monospace",
            color: 'var(--text-primary)',
            pointerEvents: 'none',
            zIndex: 10,
            boxShadow: '0 0 12px rgba(0, 255, 136, 0.1)',
            whiteSpace: 'pre-line',
          }}
        >
          {tooltip.text}
        </div>
      )}
    </div>
  );
});

export default DeckMapInner;
