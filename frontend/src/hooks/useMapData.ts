import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export function useBusStopsHourly(hour: number) {
  return useQuery({
    queryKey: ['busStopsHourly', hour],
    queryFn: () => api.busStopsHourly(hour),
  });
}

export function useBusStopsHourlyFull() {
  return useQuery({
    queryKey: ['busStopsHourlyFull'],
    queryFn: () => api.busStopsHourlyFull(),
  });
}

export function useBusStopDetail(stopId: number | null) {
  return useQuery({
    queryKey: ['busStopDetail', stopId],
    queryFn: () => api.busStopHourlyAll(stopId!),
    enabled: stopId !== null,
  });
}

export function useSubwayStations() {
  return useQuery({ queryKey: ['subwayStations'], queryFn: api.subwayStations });
}

export function useSubwayEntrances() {
  return useQuery({ queryKey: ['subwayEntrances'], queryFn: api.subwayEntrances });
}

export function useSubwayPolygons() {
  return useQuery({ queryKey: ['subwayPolygons'], queryFn: api.subwayPolygons });
}

export function useSubwayHourly() {
  return useQuery({ queryKey: ['subwayHourly'], queryFn: api.subwayHourly });
}

export function useRiskPoints() {
  return useQuery({ queryKey: ['riskPoints'], queryFn: api.riskPoints });
}

export function useTraffic() {
  return useQuery({ queryKey: ['traffic'], queryFn: () => api.traffic() });
}

export function useTrafficPattern() {
  return useQuery({
    queryKey: ['trafficPattern'],
    queryFn: () => api.trafficPattern(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useTrafficRealtime(enabled: boolean) {
  return useQuery({
    queryKey: ['trafficRealtime'],
    queryFn: () => api.trafficRealtime(),
    enabled,
    refetchInterval: 5 * 60 * 1000,
    staleTime: 4 * 60 * 1000,
  });
}

export function useFoottraffic() {
  return useQuery({ queryKey: ['foottraffic'], queryFn: api.foottraffic });
}

export function useStores() {
  return useQuery({ queryKey: ['stores'], queryFn: () => api.stores() });
}

export function useStoresSummary() {
  return useQuery({ queryKey: ['storesSummary'], queryFn: api.storesSummary });
}

export function useBuildings() {
  return useQuery({ queryKey: ['buildings'], queryFn: api.buildings });
}

export function useSalary() {
  return useQuery({ queryKey: ['salary'], queryFn: () => api.salary() });
}

export function useKraftonCluster() {
  return useQuery({ queryKey: ['kraftonCluster'], queryFn: api.kraftonCluster });
}

export function useCommercialArea() {
  return useQuery({ queryKey: ['commercialArea'], queryFn: api.commercialArea });
}

export function useCrossAnalysis() {
  return useQuery({ queryKey: ['crossAnalysis'], queryFn: api.crossAnalysis });
}
