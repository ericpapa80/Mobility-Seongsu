import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter(tags=["map-data"])

logger = logging.getLogger(__name__)

PIPELINE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "pipeline"
REF_DIR = PIPELINE_DIR / "ref"
SILVER_DIR = PIPELINE_DIR / "silver"

RISK_POINTS = [
    {"name": "공사구간", "lat": 37.5435, "lng": 127.0610, "risk": "high"},
    {"name": "행사구간", "lat": 37.5490, "lng": 127.0550, "risk": "mid"},
]

DATA_SOURCES = [
    {
        "id": "bus",
        "cluster": "flow",
        "name": "버스 정류장",
        "provider": "서울열린데이터광장 (CardBusTimeNew) / data.seoul.go.kr",
        "free": "무료 (공공누리 1유형)",
        "schedule": "월별, 매월 5일 전월 데이터 갱신",
        "unit": "월별·노선별·정류장별·시간대별(00~23시) 승하차",
        "api": "REST API (openapi.seoul.go.kr:8088)",
        "usage": "버스 승하차 패턴, 정류장별 이용량, 교통카드 기반 분석",
        "target": "성수동 인근 정류장 (ws.bus.go.kr 정류소정보 + CardBusTimeNew)",
        "storage": "DB 또는 Silver JSON",
        "status": "active",
    },
    {
        "id": "subway",
        "cluster": "flow",
        "name": "지하철 (역사·출구·시간대별)",
        "provider": "서울열린데이터광장 (CardSubwayTime) / 서울교통공사 15143845 (공공데이터포털)",
        "free": "무료",
        "schedule": "CardSubwayTime: 월별 매월 5일 전월 / 15143845: 최근 7일 매일 3일 전 갱신",
        "unit": "월별 또는 일별·호선별·역별·시간대별(06시이전~24시이후) 승하차",
        "api": "REST API (OpenAPI/SHEET/FILE)",
        "usage": "역별 승하차 패턴, 시간대별 이용량, 교통카드 기반 분석",
        "target": "1~9호선·신분당선·공항철도 (성수·뚝섬·건대입구·서울숲 포함)",
        "storage": "DB 또는 Silver JSON",
        "status": "active",
    },
    {
        "id": "subway_congestion_sk",
        "cluster": "flow",
        "name": "지하철 혼잡도 (실시간)",
        "provider": "SK Open API (openapi.sk.com) 지하철 혼잡도",
        "free": "유료 (Free: 월 10건, Basic: 11원/건 월 3천건 또는 33원/건 일 100건)",
        "schedule": "실시간 + 통계성, 10분 단위 (05:30~23:50)",
        "unit": "10분 단위·열차/칸별 혼잡도(%)·칸별 하차 비율·출구 통행자 수",
        "api": "REST API (apis.openapi.sk.com/transit/puzzle/subway/congestion)",
        "usage": "실시간 혼잡도 대시보드, 칸별 하차 비율, 출구별 통행자 통계",
        "target": "수도권 1~9호선·신분당선·공항철도 전체 (서울교통공사·SK텔레콤·티맵 협력)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "traffic_realtime",
        "cluster": "flow",
        "name": "교통 속도 (실시간)",
        "provider": "서울열린데이터광장 (TOPIS TrafficInfo) / openapi.seoul.go.kr",
        "free": "무료",
        "schedule": "실시간 제공, 수집 5분 주기 (cron-job.org), TTL 5분 캐시",
        "unit": "LINK_ID별·속도(km/h)·소통상태·통행시간",
        "api": "REST API (XML), LINK_ID별 개별 조회",
        "usage": "도로별 실시간 소통 상태, 속도 시각화, DB 적재·JSONL 백업",
        "target": "성수 권역 도로 링크 (topis_seongsu_links.json)",
        "storage": "DB + JSONL 백업",
        "status": "active",
    },
    {
        "id": "traffic_pattern",
        "cluster": "flow",
        "name": "교통 속도 (패턴)",
        "provider": "서울열린데이터광장 (TOPIS) 도로별 일자별 통행속도 XLSX",
        "free": "무료",
        "schedule": "XLSX 수동 다운로드 후 변환",
        "unit": "도로별·일자별·시간대별 통행속도",
        "api": "XLSX 파일 다운로드 (수동)",
        "usage": "평일/주말 시간대별 패턴 분석, topis_traffic_pattern.json",
        "target": "성수 권역 도로",
        "storage": "ref/topis_traffic_pattern.json",
        "status": "active",
    },
    {
        "id": "traffic_historical",
        "cluster": "flow",
        "name": "교통 속도 (과거)",
        "provider": "서울열린데이터광장 (TOPIS) Silver 변환",
        "free": "무료",
        "schedule": "수동 갱신",
        "unit": "도로별·시간대별(0~23시) 속도",
        "api": "Silver 변환 결과 (traffic_seongsu.json)",
        "usage": "과거 속도 이력, 트렌드 분석",
        "target": "성수 권역 도로",
        "storage": "DB 또는 Silver JSON",
        "status": "active",
    },
    {
        "id": "foottraffic",
        "cluster": "flow",
        "name": "보행자 통행량",
        "provider": "서울특별시 골목길 유동인구 (golmok.seoul.go.kr)",
        "free": "무료",
        "schedule": "2025년 3분기 기준, 수동 수집 (분기별 갱신)",
        "unit": "골목길 링크별·시간대(00~05~21~23)·요일(주중/주말)·연령대·acost",
        "api": "POST API (fpop.json, 세션·쿠키 필요, TM좌표계)",
        "usage": "보행 밀도, 상권·교통 연계 분석, CCTV·교통 노선 설계",
        "target": "성수동 골목길 (signguCd=11, 좌표 범위 지정)",
        "storage": "DB 또는 Silver JSON",
        "status": "active",
    },
    {
        "id": "foottraffic_sk",
        "cluster": "flow",
        "name": "유동인구 (실시간)",
        "provider": "SK Open API (지오비전 퍼즐 puzzle.geovision.co.kr)",
        "free": "유료 (Free: 월 10건, Basic: 11~33원/건)",
        "schedule": "실시간 (기지국 신호·Call 신호 기반)",
        "unit": "50m² pCell 단위, 성별·연령별, 거주/직장/방문인구, 기점-종점 통행",
        "api": "REST API (유동인구·서비스인구·기점종점통행 API)",
        "usage": "실시간 유동인구, 교통 노선 설계, 상권·CCTV 위치 분석",
        "target": "전국 250개 시군구 (pCell 측위, GPS 음영 구역 대응)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "place_congestion_sk",
        "cluster": "commercial",
        "name": "장소 혼잡도",
        "provider": "SK Open API (TMAP puzzle 장소 혼잡도)",
        "free": "유료 (Free: 월 10건, Basic: 11~33원/건)",
        "schedule": "준실시간",
        "unit": "POI별 혼잡도, 방문자 통계(연령·유입력)",
        "api": "REST API (실시간 장소 혼잡도)",
        "usage": "쇼핑·여가 장소 혼잡도, 상권 분석",
        "target": "쇼핑·여가 장소(POI)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "bike_seoul",
        "cluster": "flow",
        "name": "공공자전거 (따릉이)",
        "provider": "서울열린데이터광장 (bikeList) / bikeseoul.com",
        "free": "무료 (공공누리 1유형)",
        "schedule": "수시(실시간)",
        "unit": "대여소별·rackTotCnt·parkingBikeTotCnt·parkingQRBikeCnt·parkingELECBikeCnt",
        "api": "REST API (openapi.seoul.go.kr:8088/.../json/bikeList/1/999, 최대 1천건/회)",
        "usage": "공유모빌리티 가용성, 대여소 밀집도, 실시간 대여 가능 수량",
        "target": "서울시 따릉이 대여소 전역 (2회 분할 호출 필요)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_population",
        "cluster": "flow",
        "name": "실시간 인구현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위), 과거 데이터 미제공",
        "unit": "장소별 현재 인구",
        "api": "REST API (1회 1장소, 장소명/장소코드 택1)",
        "usage": "foottraffic(골목길 분기) 대비 실시간 보강",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_traffic",
        "cluster": "flow",
        "name": "도로소통현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "장소별 도로 소통 상태",
        "api": "REST API (1회 1장소)",
        "usage": "traffic_realtime(TOPIS)와 중복 가능, 122장소 단위 보완",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_parking",
        "cluster": "infrastructure",
        "name": "주차장 현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "장소별 주차 가능 대수 등",
        "api": "REST API (1회 1장소)",
        "usage": "상권 접근성·주차 수요 파악",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_subway_arrival",
        "cluster": "flow",
        "name": "지하철 실시간 도착",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "역별 도착 예정 시각",
        "api": "REST API (1회 1장소)",
        "usage": "subway(승하차) 보강, 혼잡 예측 보조",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_bus_arrival",
        "cluster": "flow",
        "name": "버스정류소 현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "정류소별 버스 도착 예정",
        "api": "REST API (1회 1장소)",
        "usage": "bus(승하차) 보강, 대중교통 실시간 체감 개선",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_accident",
        "cluster": "risk",
        "name": "사고통제현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "사고·통제 구간",
        "api": "REST API (1회 1장소)",
        "usage": "risk(데모) 실데이터 보강",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_bike",
        "cluster": "flow",
        "name": "따릉이 현황 (122장소)",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "장소별 대여소 가용 수",
        "api": "REST API (1회 1장소)",
        "usage": "bike_seoul(bikeList)와 상호 보완, 122장소 단위",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_weather",
        "cluster": "risk",
        "name": "날씨 현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "기온·강수 등",
        "api": "REST API (1회 1장소)",
        "usage": "유동인구·이용 패턴 보조 변수",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_ev_charger",
        "cluster": "infrastructure",
        "name": "전기차충전소 현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "충전소 가용성",
        "api": "REST API (1회 1장소)",
        "usage": "모빌리티 인프라 지표",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_culture",
        "cluster": "risk",
        "name": "문화행사 현황",
        "provider": "서울열린데이터광장 (OA-21285) / data.seoul.go.kr/SeoulRtd",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간 (분단위)",
        "unit": "행사 일정·장소",
        "api": "REST API (1회 1장소)",
        "usage": "행사일 유동 급증 예측, 이벤트 기반 분석",
        "target": "성수역·뚝섬역 주변 (122장소)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "seoul_realtime_commercial",
        "cluster": "commercial",
        "name": "실시간 상권현황데이터",
        "provider": "서울열린데이터광장 (OA-22385) / data.seoul.go.kr",
        "free": "무료 (공공누리 1유형)",
        "schedule": "실시간",
        "unit": "상권별 실시간 현황",
        "api": "REST API (상권 범위)",
        "usage": "상권 전용 API, stores·foottraffic 보완",
        "target": "성수동 상권 (OA-22385 상권 단위)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "stores",
        "cluster": "commercial",
        "name": "상가 분포",
        "provider": "OpenUp (건물·매장 매출 추정, 비공개 API)",
        "free": "유료 (상용 서비스, 웹 크롤링)",
        "schedule": "access-token 주기적 갱신, cell-token 고정, 수동 수집",
        "unit": "건물·매장별·시간대(아침~새벽)·요일·성연령·매출 추정",
        "api": "웹 크롤링 (/v2/pro/bd/hash, /v2/pro/bd/sales, F12 Network 토큰 수집)",
        "usage": "상권 매출 추정, 시간대별 소비 패턴, 건물별 매장 목록",
        "target": "성수동 건물·매장 (cell-token 지역별)",
        "storage": "DB 또는 Silver JSON",
        "status": "active",
    },
    {
        "id": "salary",
        "cluster": "commercial",
        "name": "사업장/급여",
        "provider": "국민연금공단 (공공데이터포털 data.go.kr/B552015/NpsBplcInfoInqireServiceV2)",
        "free": "무료",
        "schedule": "수시 갱신 (2025.5.7 API v2 전환, 자료생성년월 기준)",
        "unit": "사업장별·업종·가입자수·금액·월급여추정·연간급여추정 (법인 3인↑, 개인 10인↑)",
        "api": "REST API (getBassInfoSearchV2, getDetailInfoSearchV2, getPdAcctoSttusInfoSearchV2)",
        "usage": "직주 근접성, 산업별 급여 수준, 상한액 적용 참고",
        "target": "성수동 인근 사업장 (법정동/행정동 코드)",
        "storage": "DB 또는 Silver JSON",
        "status": "active",
    },
    {
        "id": "buildings",
        "cluster": "commercial",
        "name": "건물",
        "provider": "국토교통부 ArchHub(건축물대장) / VWorld(3D 폐쇄) GeoJSON 참조",
        "free": "무료 (ArchHub: 공공데이터 10천회/월, VWorld 3D API 2019 폐쇄)",
        "schedule": "정적 참조 (hub.go.kr, data.go.kr/15134735)",
        "unit": "건물 폴리곤, 층별개요, 표제부",
        "api": "로컬 GeoJSON (ArchHub REST JSON/XML, VWorld WMTS/TMS 배경지도)",
        "usage": "건물 경계, 공간 분석, 3D Desktop API·WebGL 3D 지도",
        "target": "성수동 (ss_pg_building.geojson)",
        "storage": "ref/ss_pg_building.geojson",
        "status": "active",
    },
    {
        "id": "ngii_road",
        "cluster": "infrastructure",
        "name": "도로·보도 (정밀도로지도)",
        "provider": "국토지리정보원 국토정보플랫폼 (map.ngii.go.kr) / 공공데이터포털",
        "free": "무료",
        "schedule": "정기 갱신 (기본공간정보 1:5,000, 정밀도로지도 data.go.kr/15059912)",
        "unit": "도로경계·차도·보도·도로폭·보도폭·도로중심선",
        "api": "REST API (WMTS) / SHP·NGI 파일 다운로드",
        "usage": "도로폭·보도폭 분석, 보행 환경 평가",
        "target": "전국 (성수동 포함)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "crosswalk_std",
        "cluster": "infrastructure",
        "name": "횡단보도 표준데이터",
        "provider": "공공데이터포털 전국횡단보도표준데이터 (15028201)",
        "free": "무료",
        "schedule": "반기(6개월) 갱신",
        "unit": "위치·횡단보도종류·보행자신호등·음향신호기·점자블록·신호시간 등 25항목",
        "api": "파일 다운로드 (XLS·XML·JSON·RDF·CSV) / API 권장",
        "usage": "횡단보도 위치·신호정보, 보행 안전 분석",
        "target": "전국 (지자체별 55개 파일)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "schoolzone_std",
        "cluster": "infrastructure",
        "name": "어린이보호구역 표준데이터",
        "provider": "공공데이터포털 전국어린이보호구역표준데이터 (15012891)",
        "free": "무료",
        "schedule": "반기(6개월) 갱신, 매월 초 전국 병합",
        "unit": "시설종류·대상시설명·위도·경도·CCTV설치·보호구역도로폭 등",
        "api": "파일 다운로드 (XLS·XML·JSON·RDF·CSV)",
        "usage": "스쿨존 위치, 보행 안전·교통 분석",
        "target": "전국 (지자체별 227건)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "archhub_permit",
        "cluster": "infrastructure",
        "name": "건축 인허가",
        "provider": "국토교통부 건축허브 (hub.go.kr) / 공공데이터포털 15136267",
        "free": "무료 (개발 10천회/월)",
        "schedule": "분기 갱신",
        "unit": "동별·층별·호별개요, 대수선, 전유공용면적, 주차장, 지역지구구역 등",
        "api": "REST API (JSON/XML)",
        "usage": "건축인허가 상세, 용도·규모 분석",
        "target": "전국 (건축HUB OPEN-API 57종)",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "smap_3d",
        "cluster": "infrastructure",
        "name": "S-Map 3D 건물",
        "provider": "서울시 스마트서울맵 (smap.seoul.go.kr) / 공공데이터포털 15061409",
        "free": "무료",
        "schedule": "연간 갱신 (항공·드론·라이다 촬영, 2024년 605㎢ 갱신)",
        "unit": "3D 건물 (고·중·저화질), 공간정보",
        "api": "Open API (XML) / 웹 크롤링 (공식 API 제한 시)",
        "usage": "3D 건물 시각화, BIM 플랫폼 연계",
        "target": "서울 전역",
        "storage": "미연동 (검토 중)",
        "status": "planned",
    },
    {
        "id": "krafton",
        "cluster": "commercial",
        "name": "크래프톤 클러스터",
        "provider": "GeoJSON 참조 (수동 구축)",
        "free": "무료",
        "schedule": "정적 참조",
        "unit": "클러스터 폴리곤",
        "api": "로컬 파일",
        "usage": "클러스터 내외 상권·유동 비교",
        "target": "크래프톤 인근",
        "storage": "ref/ss_pg_krafton_cluster.geojson",
        "status": "active",
    },
    {
        "id": "commercial_area",
        "cluster": "commercial",
        "name": "상권 경계",
        "provider": "GeoJSON 참조 (수동 구축)",
        "free": "무료",
        "schedule": "정적 참조",
        "unit": "상권 폴리곤",
        "api": "로컬 파일",
        "usage": "상권 구역 시각화",
        "target": "성수동",
        "storage": "ref/ss_pg_commercial_area.geojson",
        "status": "active",
    },
    {
        "id": "risk",
        "cluster": "risk",
        "name": "위험 구간",
        "provider": "데모 데이터",
        "free": "무료",
        "schedule": "정적",
        "unit": "포인트 (lat, lng, risk)",
        "api": "메모리",
        "usage": "데모·시연용",
        "target": "성수동",
        "storage": "메모리",
        "status": "active",
    },
]


_cache: dict[str, object] = {}


def _load_silver(filename: str) -> dict:
    if filename not in _cache:
        with open(SILVER_DIR / filename, encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]


def _load_geojson(filename: str) -> dict:
    with open(REF_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


# ── DB-first helpers (각 함수는 DB 조회 성공 시 결과 반환, 실패 시 None) ──

async def _db_get_traffic(hour: Optional[int] = None) -> Optional[dict]:
    """traffic_segments 테이블에서 교통속도 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                "SELECT link_id, road_name, direction, distance, lanes, road_type, area_type, "
                "speeds, coordinates FROM traffic_segments"
            ))).all()
        if not rows:
            return None
        segments = []
        for r in rows:
            sp = r.speeds or []
            seg = {
                "link_id": r.link_id,
                "road_name": r.road_name or "",
                "direction": r.direction or "",
                "distance": r.distance or 0,
                "lanes": r.lanes or 1,
                "road_type": r.road_type or "",
                "area_type": r.area_type or "",
                "speeds": sp,
                "coordinates": r.coordinates or [],
            }
            if hour is not None and sp:
                seg["speed"] = sp[hour] if hour < len(sp) else 0
            segments.append(seg)
        return {"meta": {"segment_count": len(segments)}, "segments": segments}
    except Exception as exc:
        logger.warning("DB traffic query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_subway_hourly() -> Optional[dict]:
    """subway_stations + subway_station_hourly 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        async with async_session() as session:
            sta_rows = (await session.execute(sa_text(
                "SELECT id, name, sub_sta_sn, use_date, lng, lat FROM subway_stations"
            ))).all()
            if not sta_rows:
                return None
            hourly_rows = (await session.execute(sa_text(
                "SELECT station_id, hour, ride, alight FROM subway_station_hourly ORDER BY station_id, hour"
            ))).all()

        hourly_map: dict[int, dict] = {}
        for h in hourly_rows:
            if h.station_id not in hourly_map:
                hourly_map[h.station_id] = {"ride": [0] * 24, "alight": [0] * 24}
            if h.hour < 24:
                hourly_map[h.station_id]["ride"][h.hour] = h.ride
                hourly_map[h.station_id]["alight"][h.hour] = h.alight

        stations = []
        use_date = sta_rows[0].use_date if sta_rows else ""
        for s in sta_rows:
            hr = hourly_map.get(s.id, {"ride": [0] * 24, "alight": [0] * 24})
            stations.append({
                "name": s.name,
                "lat": s.lat,
                "lng": s.lng,
                "sub_sta_sn": s.sub_sta_sn,
                "ridership": hr,
            })
        return {"meta": {"date": use_date, "station_count": len(stations)}, "stations": stations}
    except Exception as exc:
        logger.warning("DB subway query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_stores(category: Optional[str] = None) -> Optional[dict]:
    """stores 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        where = "WHERE category_bg = :cat" if category else ""
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                f"SELECT store_id, name, road_address, category_bg, category_mi, category_sl, "
                f"lng, lat, peco_total, peco_individual, "
                f"peco_corporate, peco_foreign, times, weekday, gender_f, gender_m "
                f"FROM stores {where}"
            ), {"cat": category} if category else {})).all()
        if not rows:
            return None
        stores = [
            {
                "store_id": r.store_id, "name": r.name, "road_address": r.road_address,
                "category_bg": r.category_bg, "category_mi": r.category_mi, "category_sl": r.category_sl,
                "lng": r.lng, "lat": r.lat,
                "peco_total": r.peco_total, "peco_individual": r.peco_individual,
                "peco_corporate": r.peco_corporate, "peco_foreign": r.peco_foreign,
                "times": r.times or {}, "weekday": r.weekday or {},
                "gender_f": r.gender_f or {}, "gender_m": r.gender_m or {},
            }
            for r in rows
        ]
        return {"meta": {"store_count": len(stores)}, "stores": stores}
    except Exception as exc:
        logger.warning("DB stores query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_salary(industry: Optional[str] = None) -> Optional[dict]:
    """salary_workplaces 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        where = "WHERE industry = :ind" if industry else ""
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                f"SELECT name, industry, employees, monthly_salary, "
                f"lng, lat FROM salary_workplaces {where}"
            ), {"ind": industry} if industry else {})).all()
        if not rows:
            return None
        workplaces = [
            {
                "name": r.name, "industry": r.industry,
                "employees": r.employees, "monthly_salary": r.monthly_salary,
                "lng": r.lng, "lat": r.lat,
            }
            for r in rows
        ]
        return {"meta": {"workplace_count": len(workplaces)}, "workplaces": workplaces}
    except Exception as exc:
        logger.warning("DB salary query failed, fallback to JSON: %s", exc)
        return None


async def _db_get_foottraffic() -> Optional[dict]:
    """foottraffic_links 테이블 조회. DB 없으면 None."""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return None
    try:
        from sqlalchemy import text as sa_text
        async with async_session() as session:
            rows = (await session.execute(sa_text(
                "SELECT road_link_id, coordinates, centroid_lng, centroid_lat, data "
                "FROM foottraffic_links"
            ))).all()
        if not rows:
            return None
        links = []
        for r in rows:
            centroid = [r.centroid_lng, r.centroid_lat] if r.centroid_lng else []
            links.append({
                "road_link_id": r.road_link_id,
                "coordinates": r.coordinates or [],
                "centroid": centroid,
                "data": r.data or {},
            })
        return {"meta": {"link_count": len(links)}, "links": links}
    except Exception as exc:
        logger.warning("DB foottraffic query failed, fallback to JSON: %s", exc)
        return None


def _build_subway_stations() -> list[dict]:
    """ss_pt_subway_statn.geojson → API 응답 형식으로 변환"""
    geo = _load_geojson("ss_pt_subway_statn.geojson")
    return [
        {
            "name": feat["properties"]["KOR_SUB_NM"],
            "lat": feat["geometry"]["coordinates"][1],
            "lng": feat["geometry"]["coordinates"][0],
            "sub_sta_sn": feat["properties"]["SUB_STA_SN"],
        }
        for feat in geo["features"]
    ]


def _build_subway_entrances() -> list[dict]:
    """ss_pt_subway_entrc.geojson → API 응답 형식으로 변환"""
    geo = _load_geojson("ss_pt_subway_entrc.geojson")
    return [
        {
            "station_name": feat["properties"]["KOR_SUB_NM"],
            "entrance_no": feat["properties"]["ENTRC_NO"],
            "lat": feat["geometry"]["coordinates"][1],
            "lng": feat["geometry"]["coordinates"][0],
            "sub_sta_sn": feat["properties"]["SUB_STA_SN"],
        }
        for feat in geo["features"]
    ]


def _build_subway_polygons() -> dict:
    """ss_pg_subway_statn.geojson → GeoJSON FeatureCollection 그대로 전달"""
    return _load_geojson("ss_pg_subway_statn.geojson")


def _load_subway_hourly() -> dict:
    with open(SILVER_DIR / "subway_stations_hourly.json", encoding="utf-8") as f:
        return json.load(f)


SUBWAY_STATIONS = _build_subway_stations()
SUBWAY_ENTRANCES = _build_subway_entrances()
SUBWAY_POLYGONS = _build_subway_polygons()
SUBWAY_HOURLY = _load_subway_hourly()


CLUSTER_LABELS = {
    "flow": "유동 흐름",
    "commercial": "상권",
    "infrastructure": "인프라",
    "risk": "안전",
    "common": "공통",
}


@router.get("/sources")
async def get_sources():
    """데이터 수집 출처·API·갱신주기 메타데이터 (클러스터별 그룹화)"""
    clusters: dict[str, list[dict]] = {
        "flow": [],
        "commercial": [],
        "infrastructure": [],
        "risk": [],
        "common": [],
    }
    for s in DATA_SOURCES:
        c = s.get("cluster", "common")
        clusters.setdefault(c, []).append(s)
    return {
        "sources": DATA_SOURCES,
        "clusters": [
            {"id": k, "label": CLUSTER_LABELS.get(k, k), "items": clusters[k]}
            for k in ("flow", "commercial", "infrastructure", "risk")
            if clusters[k]
        ],
    }


@router.get("/subway-stations")
async def get_subway_stations():
    return {"stations": SUBWAY_STATIONS}


@router.get("/subway-entrances")
async def get_subway_entrances():
    return {"entrances": SUBWAY_ENTRANCES}


@router.get("/subway-polygons")
async def get_subway_polygons():
    return SUBWAY_POLYGONS


@router.get("/subway-hourly")
async def get_subway_hourly():
    db_result = await _db_get_subway_hourly()
    if db_result:
        return db_result
    return SUBWAY_HOURLY


@router.get("/risk-points")
async def get_risk_points():
    return {"points": RISK_POINTS}


# ── New GeoJSON-backed endpoints ──────────────────────────────────

@router.get("/traffic")
async def get_traffic(hour: Optional[int] = Query(None, ge=0, le=23)):
    db_result = await _db_get_traffic(hour)
    if db_result:
        if hour is not None:
            db_result["hour"] = hour
        return db_result
    # JSON fallback
    data = _load_silver("traffic_seongsu.json")
    if hour is not None:
        segments = [{**seg, "speed": seg["speeds"][hour]} for seg in data["segments"]]
        return {"meta": data["meta"], "hour": hour, "segments": segments}
    return data


@router.get("/traffic/pattern")
async def get_traffic_pattern():
    """TOPIS 과거 데이터 기반 평일/주말 시간대별 패턴"""
    key = "topis_traffic_pattern.json"
    if key not in _cache:
        path = REF_DIR / key
        if not path.exists():
            return {"error": "pattern data not found", "overall": None, "roads": {}}
        with open(path, encoding="utf-8") as f:
            _cache[key] = json.load(f)
    data = _cache[key]
    return data


@router.get("/traffic/realtime/status")
async def get_traffic_realtime_status():
    """traffic_realtime_log 적재 현황 — 크론잡 동작 확인용"""
    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return {"db": False, "total_rows": 0, "latest": None, "oldest": None}

    from sqlalchemy import text as sa_text
    async with async_session() as session:
        row = (await session.execute(sa_text("""
            SELECT
                COUNT(*)                             AS total_rows,
                MAX(fetched_at) AT TIME ZONE 'Asia/Seoul' AS latest,
                MIN(fetched_at) AT TIME ZONE 'Asia/Seoul' AS oldest,
                COUNT(DISTINCT DATE_TRUNC('minute', fetched_at)) AS collection_count
            FROM traffic_realtime_log
        """))).one()
    return {
        "db": True,
        "total_rows": row.total_rows,
        "collection_count": row.collection_count,
        "latest": row.latest.isoformat() if row.latest else None,
        "oldest": row.oldest.isoformat() if row.oldest else None,
    }


@router.get("/traffic/realtime/collect")
async def collect_traffic_realtime():
    """크론잡 전용 — 수집 후 최소 응답만 반환 (좌표 제외)"""
    from app.config import get_settings
    from app.services.topis_client import get_topis_client

    settings = get_settings()
    if not settings.SEOUL_OPEN_DATA_KEY:
        return {"ok": False, "reason": "no_api_key"}

    client = get_topis_client(settings.SEOUL_OPEN_DATA_KEY)
    result = await client.get_realtime()
    return {
        "ok": True,
        "collected": result.get("meta", {}).get("segment_count", 0),
        "fetched_at": result.get("meta", {}).get("fetched_at"),
    }


@router.get("/traffic/realtime")
async def get_traffic_realtime():
    """TOPIS 실시간 도로 소통 정보 (5분 캐시)"""
    from app.config import get_settings
    from app.services.topis_client import get_topis_client

    settings = get_settings()
    if not settings.SEOUL_OPEN_DATA_KEY:
        return {"error": "SEOUL_OPEN_DATA_KEY not configured", "segments": []}

    client = get_topis_client(settings.SEOUL_OPEN_DATA_KEY)
    return await client.get_realtime()


@router.get("/traffic/realtime/history")
async def get_traffic_realtime_history(
    compare: str = Query("yesterday", regex="^(yesterday|last_week|hours_24)$"),
):
    """DB에 축적된 실시간 이력에서 비교 데이터 조회

    compare:
      - yesterday: 어제 같은 시간대 (±30분)
      - last_week: 지난주 같은 요일 같은 시간대 (±30분)
      - hours_24: 최근 24시간 시간대별 평균
    """
    from datetime import datetime, timedelta, timezone

    from app.db.database import is_db_available, async_session
    if not is_db_available() or async_session is None:
        return {"error": "DB not available", "data": None}

    from sqlalchemy import select, func as sa_func, extract
    from app.db.models import TrafficRealtimeLog

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)

    async with async_session() as session:
        if compare == "hours_24":
            cutoff = now - timedelta(hours=24)
            stmt = (
                select(
                    extract("hour", TrafficRealtimeLog.fetched_at).label("hour"),
                    sa_func.avg(TrafficRealtimeLog.speed).label("avg_speed"),
                    sa_func.count().label("samples"),
                )
                .where(TrafficRealtimeLog.fetched_at >= cutoff)
                .group_by("hour")
                .order_by("hour")
            )
            rows = (await session.execute(stmt)).all()
            data = [
                {"hour": int(r.hour), "avg_speed": round(float(r.avg_speed), 2), "samples": r.samples}
                for r in rows
            ]
            return {"compare": compare, "reference_time": now.isoformat(), "data": data}

        if compare == "yesterday":
            ref_time = now - timedelta(days=1)
        else:  # last_week
            ref_time = now - timedelta(weeks=1)

        window_start = ref_time - timedelta(minutes=30)
        window_end = ref_time + timedelta(minutes=30)

        stmt = (
            select(
                sa_func.avg(TrafficRealtimeLog.speed).label("avg_speed"),
                sa_func.avg(TrafficRealtimeLog.travel_time).label("avg_travel_time"),
                sa_func.count().label("samples"),
            )
            .where(TrafficRealtimeLog.fetched_at >= window_start)
            .where(TrafficRealtimeLog.fetched_at <= window_end)
        )
        row = (await session.execute(stmt)).one_or_none()

        if row and row.samples > 0:
            data = {
                "avg_speed": round(float(row.avg_speed), 2),
                "avg_travel_time": round(float(row.avg_travel_time), 2),
                "samples": row.samples,
                "window": {
                    "start": window_start.isoformat(),
                    "end": window_end.isoformat(),
                },
            }
        else:
            data = None

        return {"compare": compare, "reference_time": ref_time.isoformat(), "data": data}


@router.get("/foottraffic")
async def get_foottraffic():
    db_result = await _db_get_foottraffic()
    if db_result:
        return db_result
    return _load_silver("foottraffic_seongsu.json")


@router.get("/stores")
async def get_stores(
    category: Optional[str] = Query(None),
    time_slot: Optional[str] = Query(None),
):
    db_result = await _db_get_stores(category)
    if db_result:
        return db_result
    # JSON fallback
    data = _load_silver("stores_seongsu.json")
    stores = data["stores"]
    if category:
        stores = [s for s in stores if s["category_bg"] == category]
    return {"meta": data["meta"], "stores": stores}


@router.get("/stores/summary")
async def get_stores_summary():
    data = _load_silver("stores_seongsu.json")
    return {"summary": data["summary"], "meta": data["meta"]}


@router.get("/buildings")
async def get_buildings():
    return _load_geojson("ss_pg_building.geojson")


@router.get("/salary")
async def get_salary(industry: Optional[str] = Query(None)):
    db_result = await _db_get_salary(industry)
    if db_result:
        return db_result
    # JSON fallback
    data = _load_silver("salary_seongsu.json")
    workplaces = data["workplaces"]
    if industry:
        workplaces = [w for w in workplaces if w["industry"] == industry]
    return {
        "meta": data["meta"],
        "summary": data["summary"],
        "workplaces": workplaces,
    }


@router.get("/krafton-cluster")
async def get_krafton_cluster():
    return _load_geojson("ss_pg_krafton_cluster.geojson")


@router.get("/commercial-area")
async def get_commercial_area():
    return _load_geojson("ss_pg_commercial_area.geojson")


@router.get("/cross-analysis")
async def get_cross_analysis():
    """보행-상권 상관, 직주 근접성, 클러스터 활력도 종합 분석"""
    import math

    foot_data = _load_silver("foottraffic_seongsu.json")
    store_data = _load_silver("stores_seongsu.json")
    salary_data = _load_silver("salary_seongsu.json")
    krafton_geo = _load_geojson("ss_pg_krafton_cluster.geojson")

    TMZON_LIST = ["00~05", "06~10", "11~13", "14~16", "17~20", "21~23"]

    # 5-1: foottraffic vs stores – 보행 밀도 상위 50 링크 주변 상가 수
    foot_links = foot_data["links"]
    stores = store_data["stores"]

    def haversine_m(lat1, lng1, lat2, lng2):
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _get_acost_allday(link: dict) -> int:
        """data 구조에서 평일 전체 종일 acost 추출 (하위호환)"""
        data = link.get("data", link.get("by_tmzon_legacy", {}))
        if "1" in data:
            return data.get("1", {}).get("00", {}).get("종일", {}).get("acost", 0)
        return data.get("종일", {}).get("acost", 0)

    top_links = sorted(
        foot_links,
        key=lambda l: _get_acost_allday(l),
        reverse=True,
    )[:50]

    foot_store_corr = []
    for link in top_links:
        cx, cy = link["centroid"]
        nearby = [s for s in stores if haversine_m(cy, cx, s["lat"], s["lng"]) <= 50]
        foot_store_corr.append({
            "link_id": link["road_link_id"],
            "acost": _get_acost_allday(link),
            "store_count": len(nearby),
            "centroid": link["centroid"],
        })

    # 5-2: work-residence proximity – 사업장 밀집 vs 지하철/버스 접근성
    workplaces = salary_data["workplaces"]
    wp_density = []
    grid_size = 0.002
    grid: dict[str, dict] = {}
    for wp in workplaces:
        gx = round(wp["lng"] / grid_size) * grid_size
        gy = round(wp["lat"] / grid_size) * grid_size
        key = f"{gx:.4f}_{gy:.4f}"
        if key not in grid:
            grid[key] = {"lng": gx, "lat": gy, "employees": 0, "count": 0, "salary_sum": 0.0}
        grid[key]["employees"] += wp["employees"]
        grid[key]["count"] += 1
        grid[key]["salary_sum"] += wp["monthly_salary"] * wp["employees"]

    for cell in grid.values():
        avg_sal = cell["salary_sum"] / cell["employees"] if cell["employees"] > 0 else 0
        wp_density.append({
            "lng": round(cell["lng"], 5),
            "lat": round(cell["lat"], 5),
            "employees": cell["employees"],
            "workplace_count": cell["count"],
            "avg_salary": round(avg_sal),
        })
    wp_density.sort(key=lambda x: -x["employees"])

    # 5-3: krafton cluster vitality – 클러스터 내 vs 외 상가 시간대 패턴
    cluster_bounds = []
    for feat in krafton_geo["features"]:
        coords = feat["geometry"]["coordinates"]
        flat_coords = []
        for ring in coords:
            if isinstance(ring[0][0], list):
                for sub in ring:
                    flat_coords.extend(sub)
            else:
                flat_coords.extend(ring)
        lngs = [c[0] for c in flat_coords]
        lats = [c[1] for c in flat_coords]
        cluster_bounds.append({
            "min_lng": min(lngs), "max_lng": max(lngs),
            "min_lat": min(lats), "max_lat": max(lats),
        })

    def in_cluster(lng, lat):
        for b in cluster_bounds:
            if b["min_lng"] <= lng <= b["max_lng"] and b["min_lat"] <= lat <= b["max_lat"]:
                return True
        return False

    time_keys = ["아침", "점심", "오후", "저녁", "밤", "심야", "새벽"]
    inside = {k: 0 for k in time_keys}
    outside = {k: 0 for k in time_keys}
    inside_count = 0
    outside_count = 0
    for s in stores:
        target = inside if in_cluster(s["lng"], s["lat"]) else outside
        counter = "inside_count" if in_cluster(s["lng"], s["lat"]) else "outside_count"
        if counter == "inside_count":
            inside_count += 1
        else:
            outside_count += 1
        for k in time_keys:
            target[k] += s.get("times", {}).get(k, 0)

    cluster_vitality = {
        "inside": {
            "count": inside_count,
            "time_profile": inside,
        },
        "outside": {
            "count": outside_count,
            "time_profile": outside,
        },
    }

    return {
        "foot_store_correlation": foot_store_corr[:30],
        "workplace_density": wp_density[:20],
        "cluster_vitality": cluster_vitality,
    }
