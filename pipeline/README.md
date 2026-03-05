# Pipeline — 성수 모빌리티 ETL

Medallion Architecture 기반 데이터 파이프라인.

## 디렉터리 구조

```
pipeline/
├── extractors/      외부 API 수집 스크립트 (Extract)
├── transforms/      정제·병합 스크립트 (Transform)
├── ref/             참조/마스터 데이터 (변경 드문 정적 파일)
├── bronze/          수집 원시 CSV (API 응답 그대로, git 제외)
│   └── archive/     과거 수집분
├── silver/          가공 완료 JSON (앱이 소비하는 SSOT, git 포함)
└── requirements.txt 파이프라인 전용 의존성
```

## 파일 네이밍 규칙

| 티어 | 패턴 | 예시 |
|------|------|------|
| **Bronze** | `{domain}__{source}__{date}[__suffix].csv` | `bus__seoul__202601.csv` |
| **Silver** | `{entity}_{granularity}.json` | `bus_stops_hourly.json` |
| **Ref** | `{domain}_{description}.{ext}` | `bus_stop_locations.csv` |
| **Extractors** | `{domain}_{desc}.py` | `bus_ridership.py` |
| **Transforms** | `build_{output}.py` | `build_bus_stops.py` |

### Bronze 필드 값

| field | values |
|-------|--------|
| domain | `bus`, `subway` |
| source | `seoul`, `sk`, `public` |
| date | `YYYYMM` 또는 `YYYYMMDD` |
| suffix | `detail`, `line7730`, `bundang` 등 (선택) |

## 워크플로

```
1. Extract:  python pipeline/extractors/bus_ridership.py -m 202601
             → pipeline/bronze/bus__seoul__202601.csv

2. Transform: python pipeline/transforms/build_bus_stops.py \
                -r pipeline/bronze/bus__seoul__202601.csv
             → pipeline/silver/bus_stops_hourly.json

3. Load:     python backend/scripts/load_bus_stops.py
             (silver JSON → PostGIS, 또는 FastAPI가 silver JSON 직접 참조)
```

## 설치

```bash
pip install -r pipeline/requirements.txt
```

`.env` 파일을 프로젝트 루트에 생성하고 API 키를 설정합니다.
