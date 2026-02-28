# 역별 시간대별 승하차인원 수집

성수역, 서울숲역, 뚝섬역, 건대입구역의 **시간대별 승하차인구**를 CSV로 수집합니다.

## 추천 방식: SK Open API (collect_subway_hourly.py)

4역 모두 지원 (서울숲역 포함). `.env`의 `PUZZLE-SUBWAY_API_KEY` 사용.  
※ API 속도제한(429) 시 역 간 5초 대기, 429 발생 시 최대 3회 재시도.

### 설치

```bash
pip install -r Collect/requirements.txt
```

### 실행

```bash
# 최신 데이터 (latest)
python Collect/collect_subway_hourly.py

# 특정 날짜 (YYYYMMDD)
python Collect/collect_subway_hourly.py -d 20260225

# 출력 경로 지정
python Collect/collect_subway_hourly.py -d 20260225 -o Collect/raw
```

### 출력

`Collect/raw/YYYYMMDD_성수권역_역별_시간대별_승하차인구.csv`

| 컬럼 | 설명 |
|------|------|
| stationName | 역명 |
| stationCode | 역코드 (211, 210, K211, 212) |
| exit | 1=승차, 2=하차, 3=환승, 4+=출구별 |
| userCount | 인원수 |
| datetime | YYYYMMDDHHMMSS |
| date | YYYY-MM-DD |
| hour | 시 (05~23) |

---

## 공공데이터 전용: getStnPsgr (collect_public_subway.py)

성수역, 뚝섬역, 건대입구역 (2호선). 서울숲역 미지원.  
한 시간 간격, 전 시간대(00~23시), 승차/하차 집계.

```bash
python Collect/collect_public_subway.py -d 20260225
```

출력: `Collect/raw/public_20260225_성수뚝섬건대_시간대별_승하차.csv`

| 컬럼 | 설명 |
|------|------|
| date | 수송일자 |
| hour | 시 (00~23) |
| stationName | 역명 |
| rideNope | 승차 인원 |
| gffNope | 하차 인원 |
| totalNope | 합계 |

### 상세 모드 (교통카드·승객구분 포함)

```bash
python Collect/collect_public_subway.py -d 20260225 --detail
```

추가 컬럼: `trnscdSeCd`, `trnscdSeCdNm`, `trnscdUserSeCd`, `trnscdUserSeCdNm`  
코드 의미: `Docs/Public_Data_api/getStnPsgr_코드_참조.md`

---

## 서울열린데이터: 버스 (collect_seoul_bus.py)

서울시 버스노선별 정류장별 시간대별 승하차 인원 (CardBusTimeNew). 월별 데이터.

```bash
# 2015년 11월 7730번 노선
python Collect/collect_seoul_bus.py -m 201511 -r 7730

# 다른 노선 / 다른 월
python Collect/collect_seoul_bus.py -m 202601 -r 2412
```

출력: `Collect/raw/seoul_bus_{YYYYMM}_노선{번호}_정류장별_시간대별_승하차.csv`

| 컬럼 | 설명 |
|------|------|
| use_ym | 사용년월 (YYYYMM) |
| rte_no | 노선번호 |
| rte_nm | 노선명 |
| stops_id | 표준버스정류장ID |
| stops_ars_no | ARS번호 |
| stops_nm | 정류장명 |
| hour | 시 (00~23) |
| rideNope | 승차 인원 |
| gffNope | 하차 인원 |

---

## 성수동 버스 정류장 24시간 수집 (2단계)

성수동 인근 모든 버스정류장의 시간대별 승하차를 수집합니다.

### 1단계: 정류장·경유노선 목록 (선택)

```bash
python Collect/fetch_seongsu_bus_stops.py
```

- 서울시 버스 API(ws.bus.go.kr)로 성수역 반경 내 정류장 + 경유노선 조회
- 필요: 공공데이터포털 **서울특별시_정류소정보조회(15000303)** 활용신청, `.env`에 `SEOUL_BUS_API_KEY` 또는 `PUBLIC_DATA_KEY`
- 실패 시 정적 목록(`seongsu_bus_routes_static.txt`) 사용

### 2단계: CardBusTimeNew 수집

```bash
python Collect/collect_seoul_bus_seongsu.py -m 202601
```

- `seongsu_bus_routes.txt`(1단계 결과) 또는 `seongsu_bus_routes_static.txt`의 노선 목록 사용
- 출력: `Collect/raw/seoul_bus_{YYYYMM}_성수동노선_정류장별_시간대별_승하차.csv`

---

## 환경 변수 (.env)

| 변수 | 용도 |
|------|------|
| PUZZLE-SUBWAY_API_KEY | SK Open API (추천) |
| PUBLIC_DATA_KEY | 공공데이터 getStnPsgr (보조) |
| SEOUL_OPEN_DATA_KEY | 서울열린데이터 (지하철·버스) |
