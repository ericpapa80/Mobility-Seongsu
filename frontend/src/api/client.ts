const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export interface BusStopBasic {
  id: number;
  ars_id: string;
  node_id: string;
  name: string;
  lat: number;
  lng: number;
  routes: string[];
  total_ride: number;
  total_alight: number;
  total: number;
}

export interface BusStopHourly extends BusStopBasic {
  ride: number;
  alight: number;
}

export interface BusStopHourlyFull {
  id: number;
  name: string;
  lat: number;
  lng: number;
  total_ride: number;
  total_alight: number;
  total: number;
  hourly: { ride: number[]; alight: number[] };
}

export interface SubwayStation {
  name: string;
  lat: number;
  lng: number;
  sub_sta_sn: number;
}

export interface SubwayEntrance {
  station_name: string;
  entrance_no: number;
  lat: number;
  lng: number;
  sub_sta_sn: number;
}

export interface GeoJSONFeature {
  type: 'Feature';
  properties: Record<string, unknown>;
  geometry: { type: string; coordinates: unknown };
}

export interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export type UserGroup = 'domestic' | 'youth' | 'child' | 'senior' | 'foreign';

export interface SubwayStationHourly {
  name: string;
  lat: number;
  lng: number;
  sub_sta_sn: number;
  ridership: { ride: number[]; alight: number[] };
  by_user_group: Record<UserGroup, number[]>;
  exit_traffic: {
    hourly_total: number[];
    by_exit: Record<string, number[]>;
  };
  total_ride: number;
  total_alight: number;
  total_exit_traffic: number;
}

export interface SubwayHourlyResponse {
  meta: { date: string; station_count: number };
  stations: SubwayStationHourly[];
}

export interface RiskPoint {
  name: string;
  lat: number;
  lng: number;
  risk: string;
}

// ── New GeoJSON-backed types ──

export interface RoadSegment {
  link_id: string;
  road_name: string;
  direction: string;
  speed: number;
  lanes: number;
  coordinates: number[][];
}

export interface TrafficSegment {
  link_id: string;
  road_name: string;
  direction: string;
  distance: number;
  lanes: number;
  road_type: string;
  area_type: string;
  speeds: number[];
  coordinates: number[][];
  speed?: number;
}

export interface TrafficResponse {
  meta: { bbox: number[]; segment_count: number; date: string };
  segments: TrafficSegment[];
  hour?: number;
}

export type TrafficPatternSpeeds = Record<string, number[]>;

export interface TrafficPatternResponse {
  meta: { months: string[]; link_count: number; total_samples: number; day_keys: string[] };
  overall: TrafficPatternSpeeds;
  roads: Record<string, TrafficPatternSpeeds>;
}

export interface TrafficRealtimeSegment {
  link_id: string;
  road_name: string;
  direction: string;
  lanes: number;
  road_type: string;
  coordinates: number[][];
  speed: number;
  travel_time: number;
}

export interface TrafficRealtimeResponse {
  meta: { bbox: number[]; segment_count: number; fetched_at: number; cache_ttl: number };
  segments: TrafficRealtimeSegment[];
}

export interface FoottrafficTmzon {
  acost: number;
  cost: number;
  grade: number;
  per: number;
}

export interface FoottrafficLink {
  road_link_id: string;
  coordinates: number[][];
  centroid: number[];
  /** data[dayweek][agrde][tmzon] = FoottrafficTmzon */
  data: Record<string, Record<string, Record<string, FoottrafficTmzon>>>;
}

export interface FoottrafficMeta {
  code: string;
  label: string;
}

export interface FoottrafficResponse {
  meta: {
    link_count: number;
    tmzon_list: string[];
    hour_to_tmzon: Record<string, string>;
    agrde_list: FoottrafficMeta[];
    dayweek_list: FoottrafficMeta[];
    max_vals: Record<string, Record<string, number>>;
  };
  links: FoottrafficLink[];
}

export interface Store {
  store_id: string;
  name: string;
  road_address: string;
  category_bg: string;
  category_mi: string;
  category_sl: string;
  lng: number;
  lat: number;
  peco_total: number;
  peco_individual: number;
  peco_corporate: number;
  peco_foreign: number;
  times: Record<string, number>;
  weekday: Record<string, number>;
  gender_f: Record<string, number>;
  gender_m: Record<string, number>;
  fam: Record<string, number>;
  wdwe: Record<string, number>;
  revfreq_weekday: number;
  revfreq_holiday: number;
  trend: StoreTrend[];
}

export interface StoreTrend {
  year: number;
  store: number;
  deli: number;
  cnt: number;
}

export interface StoresResponse {
  meta: { store_count: number };
  stores: Store[];
}

export interface StoreSummary {
  by_category: Record<string, number>;
  time_profile: Record<string, number>;
  weekday_profile: Record<string, number>;
}

export interface StoreSummaryResponse {
  summary: StoreSummary;
  meta: { store_count: number };
}

export interface Workplace {
  name: string;
  industry: string;
  employees: number;
  monthly_salary: number;
  annual_salary: number;
  per_person: number;
  active: boolean;
  lng: number;
  lat: number;
  address: string;
}

export interface IndustrySummary {
  industry: string;
  count: number;
  total_employees: number;
  avg_monthly_salary: number;
}

export interface SalaryResponse {
  meta: { workplace_count: number; active_count: number; total_employees: number };
  summary: { by_industry: IndustrySummary[]; avg_monthly_salary: number };
  workplaces: Workplace[];
}

export interface FootStoreCorrelation {
  link_id: string;
  acost: number;
  store_count: number;
  centroid: number[];
}

export interface WorkplaceDensity {
  lng: number;
  lat: number;
  employees: number;
  workplace_count: number;
  avg_salary: number;
}

export interface ClusterVitality {
  inside: { count: number; time_profile: Record<string, number> };
  outside: { count: number; time_profile: Record<string, number> };
}

export interface CrossAnalysisResponse {
  foot_store_correlation: FootStoreCorrelation[];
  workplace_density: WorkplaceDensity[];
  cluster_vitality: ClusterVitality;
}

export const api = {
  busStops: () => fetchJson<{ stops: BusStopBasic[] }>('/api/bus-stops'),
  busStopsHourly: (hour: number) =>
    fetchJson<{ hour: number; stops: BusStopHourly[] }>(`/api/bus-stops/hourly?hour=${hour}`),
  busStopHourlyAll: (stopId: number) =>
    fetchJson<BusStopBasic & { hourly: { hour: number; ride: number; alight: number }[] }>(
      `/api/bus-stops/${stopId}/hourly-all`,
    ),
  busStopsHourlyFull: () =>
    fetchJson<{ stops: BusStopHourlyFull[] }>('/api/bus-stops/hourly-full'),
  subwayStations: () => fetchJson<{ stations: SubwayStation[] }>('/api/subway-stations'),
  subwayEntrances: () => fetchJson<{ entrances: SubwayEntrance[] }>('/api/subway-entrances'),
  subwayPolygons: () => fetchJson<GeoJSONCollection>('/api/subway-polygons'),
  subwayHourly: () => fetchJson<SubwayHourlyResponse>('/api/subway-hourly'),
  riskPoints: () => fetchJson<{ points: RiskPoint[] }>('/api/risk-points'),

  traffic: (hour?: number) =>
    fetchJson<TrafficResponse>(hour !== undefined ? `/api/traffic?hour=${hour}` : '/api/traffic'),
  trafficPattern: () => fetchJson<TrafficPatternResponse>('/api/traffic/pattern'),
  trafficRealtime: () => fetchJson<TrafficRealtimeResponse>('/api/traffic/realtime'),
  foottraffic: () => fetchJson<FoottrafficResponse>('/api/foottraffic'),
  stores: (category?: string) =>
    fetchJson<StoresResponse>(category ? `/api/stores?category=${category}` : '/api/stores'),
  storesSummary: () => fetchJson<StoreSummaryResponse>('/api/stores/summary'),
  buildings: () => fetchJson<GeoJSONCollection>('/api/buildings'),
  salary: (industry?: string) =>
    fetchJson<SalaryResponse>(industry ? `/api/salary?industry=${industry}` : '/api/salary'),
  kraftonCluster: () => fetchJson<GeoJSONCollection>('/api/krafton-cluster'),
  commercialArea: () => fetchJson<GeoJSONCollection>('/api/commercial-area'),
  crossAnalysis: () => fetchJson<CrossAnalysisResponse>('/api/cross-analysis'),
};
