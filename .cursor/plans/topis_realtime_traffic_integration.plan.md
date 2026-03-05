---
name: ""
overview: ""
todos: []
isProject: false
---

# TOPIS 실시간 교통속도 API 연동 계획

## 개요

현재 정적 GeoJSON 기반의 24시간 패턴 교통속도 데이터를 유지하면서,
TOPIS 실시간 도로 소통 API를 연동하여 실시간 교통속도 시각화를 추가한다.

## 현재 상태

- `pipeline/ref/ss_pl_traffic.geojson` → `build_traffic_seongsu.py` → `pipeline/silver/traffic_seongsu.json`
- 백엔드 `GET /api/traffic` → silver JSON 메모리 캐시 반환
- 프론트엔드: PathLayer + TrafficSpeedChart (24시간 패턴)
- 성수 bbox: `127.035–127.070, 37.533–37.557` (기존)

## 참조 자료 위치

- `pipeline/source/topis/서울시+실시간+도로+소통+정보.xls` — API 명세 (TrafficInfo)
- `pipeline/source/topis/서울시+교통소통+표준링크+매핑정보.xls` — API 명세 (trafficMlrdLinkInfo)
- `pipeline/source/topis/서비스링크 보간점 정보(LINK_VERTEX)_2025.xlsx` — 정적 좌표 데이터
- `pipeline/source/topis/서울시 도로 기능별 구분 정보_2025.xlsx` — 정적 도로속성 데이터

## 확장 bbox

기존보다 넓게 설정하여 성수 주변 권역까지 포함:

- **기존**: `127.035–127.070, 37.533–37.557`
- **확장**: `127.025–127.080, 37.525–37.565`

## 작업 단계

### 1단계: 정적 참조 데이터 구축 (pipeline) ✅

- `pipeline/transforms/parse_topis_seongsu_links.py` — XLSX 파싱 + 병합
  - 서비스링크 보간점 XLSX: GRS80TM(EPSG:5181) → WGS84 좌표 변환 (pyproj)
  - 도로 기능별 구분 XLSX: 도로축코드→도로명/기능유형 매핑
  - 확장 bbox 필터: 5,093 → **252개 링크** → `pipeline/ref/topis_seongsu_links.json`

### 2단계: 백엔드 실시간 엔드포인트 (backend) ✅

- `backend/app/config.py`에 `SEOUL_OPEN_DATA_KEY` 추가
- `backend/app/services/topis_client.py` — 비동기 병렬 API 호출
  - httpx AsyncClient, Semaphore(30) 동시 호출
  - TOPIS TrafficInfo API: **XML only** (json 미지원), LINK_ID 필수
  - 252개 링크 전체 약 **3초** 소요
  - 메모리 캐시 TTL 5분
- `backend/app/api/map_data.py`에 `GET /api/traffic/realtime` 추가
  - 응답: `{ meta, segments: [{ link_id, coordinates, speed, travel_time }, ...] }`

### 3단계: 프론트엔드 실시간 연동 (frontend) ✅

- `api/client.ts` — `TrafficRealtimeSegment`, `TrafficRealtimeResponse`, `api.trafficRealtime()` 추가
- `hooks/useMapData.ts` — `useTrafficRealtime(enabled)` 훅 (5분 자동 갱신, staleTime 4분)
- `Sidebar.tsx` — `TrafficMode` 타입, 교통 속도 "패턴/실시간" 토글 + 갱신 시각 표시
- `DeckMap.tsx` — 모드별 PathLayer 분기 (pattern: `traffic-speed`, realtime: `traffic-speed-realtime`) + tooltip
- `Dashboard.tsx` — `trafficMode` 상태, `useTrafficRealtime` 훅 연결, props 전달

## 데이터 흐름

```
[기존 유지 — pattern 모드]
  silver/traffic_seongsu.json → GET /api/traffic → 24h 패턴 차트/지도

[신규 — realtime 모드]
  ref/topis_seongsu_links.json (좌표+속성, 정적)
       ↓
  backend topis_client.py → TOPIS TrafficInfo API (XML, 비동기 병렬, 5분 캐시)
       ↓
  GET /api/traffic/realtime → 프론트 PathLayer 실시간 색상 + tooltip
```

## API 상세

### TOPIS TrafficInfo

- URL: `http://openapi.seoul.go.kr:8088/{KEY}/xml/TrafficInfo/1/1/{LINK_ID}`
- 응답 형식: XML only (json 요청 시 ERROR-301)
- 출력: `<link_id>`, `<prcs_spd>` (속도 km/h), `<prcs_trv_time>` (여행시간 초)
- 제한: LINK_ID 필수 (1건씩 조회), 1회 최대 1000건

### TOPIS trafficMlrdLinkInfo

- URL: `http://openapi.seoul.go.kr:8088/{KEY}/xml/trafficMlrdLinkInfo/{START}/{END}/`
- 출력: `SRVC_LINK_ID`, `STD_LINK_NUM`, `STD_LINK_ID`
- 용도: 서비스링크 ↔ 표준링크 매핑 (향후 도로명 매핑에 활용 가능)

### 4단계: UX 개선 ✅

- **TimeSlider 실시간 배지**: 교통 실시간 모드일 때 "교통: 실시간" 배지 표시 + 현재 시각 자동 동기화 + now-marker
- **TrafficSpeedChart 실시간 마커**: 패턴(24시간) 차트 위에 실시간 평균속도를 ★ 마커로 오버레이
  - 패턴 대비 차이값(+/-) 표시
  - 차트 타이틀/서브타이틀도 모드별 변경

### 5단계: 과거 데이터 통합 ✅

- `pipeline/source/topis/` — 14개월치 XLSX (2025.01~2026.02, 서울시 차량통행속도)
- `pipeline/transforms/build_traffic_pattern.py` — 14개 XLSX 파싱, 성수 252개 링크 필터, 평일/주말/전체 패턴 집계
  - 전체 2,153,125행 중 106,848행 매칭 → 37개 도로, 256만 샘플
- `pipeline/ref/topis_traffic_pattern.json` — 출력 (평일/주말/전체 × 24시간 × 37도로)
- `backend/app/api/map_data.py` — `GET /api/traffic/pattern` 엔드포인트 추가
- `frontend/src/api/client.ts` — `TrafficPatternResponse` 타입, `api.trafficPattern()` 추가
- `frontend/src/hooks/useMapData.ts` — `useTrafficPattern()` 훅 (staleTime 30분)
- `frontend/src/components/TrafficSpeedChart.tsx` — 실시간 모드 시:
  - 평일 패턴 (파란 점선) + 주말 패턴 (주황 점선) 오버레이
  - 오늘이 평일/주말인지 자동 판별 → 해당 패턴 면적 채움
  - ★ 실시간 마커에 "평일패턴대비" 또는 "주말패턴대비" 차이값 표시
  - 범례: ┅ 평일 패턴, ┅ 주말 패턴, ★ 실시간, (14개월 평균)

### 6단계: 실시간 데이터 축적 (DB + JSONL) ✅

- **DB (PostgreSQL)**: `traffic_realtime_log` 테이블 — 90일 롤링, 인터랙티브 쿼리
  - 스키마: `(id, fetched_at, link_id, speed, travel_time)`
  - 252링크 × 288회/일 = ~72K행/일, 90일 = ~650만행
  - 하루 1회 자동 cleanup (90일 초과 삭제)
- **JSONL 백업**: `pipeline/bronze/topis_realtime/YYYYMMDD.jsonl` — 영구 아카이브
- **비교 API**: `GET /api/traffic/realtime/history?compare=yesterday|last_week|hours_24`
  - yesterday: 어제 같은 시간대 (±30분) 평균속도
  - last_week: 지난주 같은 요일 같은 시간대 평균속도
  - hours_24: 최근 24시간 시간대별 평균

## 생성/수정된 파일


| 파일                                                 | 상태  | 설명                           |
| -------------------------------------------------- | --- | ---------------------------- |
| `pipeline/transforms/parse_topis_seongsu_links.py` | 신규  | XLSX → ref JSON 변환 스크립트      |
| `pipeline/ref/topis_seongsu_links.json`            | 신규  | 성수 252개 링크 좌표+속성             |
| `backend/app/services/topis_client.py`             | 신규  | TOPIS 실시간 API + DB적재 + JSONL |
| `backend/app/config.py`                            | 수정  | SEOUL_OPEN_DATA_KEY 추가       |
| `backend/app/api/map_data.py`                      | 수정  | realtime + pattern + history |
| `backend/app/db/models.py`                         | 수정  | TrafficRealtimeLog 모델 추가    |
| `backend/scripts/init_db.sql`                      | 수정  | traffic_realtime_log 테이블     |
| `frontend/src/api/client.ts`                       | 수정  | 실시간+패턴 타입+메서드 추가            |
| `frontend/src/hooks/useMapData.ts`                 | 수정  | useTrafficRealtime/Pattern 훅 |
| `frontend/src/components/Sidebar.tsx`              | 수정  | TrafficMode, 패턴/실시간 토글       |
| `frontend/src/components/DeckMap.tsx`              | 수정  | 실시간 PathLayer + tooltip      |
| `frontend/src/components/TimeSlider.tsx`           | 수정  | 실시간 배지, 현재시각 동기화, now-marker |
| `frontend/src/components/TrafficSpeedChart.tsx`    | 수정  | 요일버튼 + 실시간★마커 + 패턴비교       |
| `frontend/src/components/RightPanel.tsx`           | 수정  | trafficMode, 패턴/실시간 데이터 전달  |
| `frontend/src/views/Dashboard.tsx`                 | 수정  | trafficMode 상태, 데이터 연결       |
| `pipeline/transforms/build_traffic_pattern.py`     | 신규  | 14개월 XLSX → 요일별 패턴 JSON      |
| `pipeline/ref/topis_traffic_pattern.json`          | 신규  | 요일별 시간대별 패턴 (37도로)          |


