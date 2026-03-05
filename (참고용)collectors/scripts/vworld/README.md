# VWorld 성수동 데이터 수집 가이드

성수동 영역의 VWorld WFS 2.0 데이터를 수집하는 스크립트입니다.

## 수집 대상 레이어

- **도로명주소건물** (`LT_C_SPBD`)
- **LX맵** (`LT_C_LANDINFOBASEMAP`)

## 주요 기능

### 1. 자동 영역 분할

- VWorld API의 **10km² bbox 제한** 및 **WFS 타일당 1000건 제한**을 고려하여 타일 분할
- 기본 타일 크기: 500m × 500m (촘촘한 수집)
- 타일이 10km²를 초과하면 자동으로 재분할

### 2. 페이지네이션 처리

- Data API의 페이지네이션을 자동으로 처리
- 기본 페이지 크기: 100건
- 모든 페이지를 자동으로 수집하여 통합

### 3. 단계별 수집 전략

1. **성수동 전체 영역을 타일로 분할**
2. **각 타일에 대해 두 레이어 순차 수집**
3. **각 레이어의 모든 페이지 수집**
4. **타일별 데이터를 레이어별로 통합 저장**

## 사용 방법

### 기본 실행

```bash
cd collectors
python scripts/vworld/collect_seongsu.py
```

### 옵션 지정

```bash
# 타일 크기 조정 (기본값: 500m)
python scripts/vworld/collect_seongsu.py --tile-size 300

# 페이지 크기 조정 (기본값: 100)
python scripts/vworld/collect_seongsu.py --page-size 50

# 요청 간 지연 시간 조정 (기본값: 0.5초)
python scripts/vworld/collect_seongsu.py --delay 1.0

# 특정 레이어만 수집
python scripts/vworld/collect_seongsu.py --layers LT_C_SPBD

# 출력 디렉토리 지정
python scripts/vworld/collect_seongsu.py --output-dir ./data/custom
```

### 전체 옵션 예시

```bash
python scripts/vworld/collect_seongsu.py \
    --tile-size 2500 \
    --page-size 100 \
    --delay 0.5 \
    --layers LT_C_SPBD LT_C_LANDINFOBASEMAP \
    --output-dir ./data/raw/vworld
```

## 출력 파일

### 1. 레이어별 통합 파일

- `seongsu_lt-c-spbd_YYYYMMDD_HHMMSS.json` / `.csv` / `.geojson` - 도로명주소건물
- `seongsu_lt-c-landinfobasemap_YYYYMMDD_HHMMSS.json` / `.csv` / `.geojson` - LX맵

### 2. 수집 요약 파일

- `seongsu_collection_summary_YYYYMMDD_HHMMSS.json` - 수집 통계 및 메타데이터

### 3. GeoJSON 자동 생성

수집 시 **레이어별 JSON 저장 직후** 같은 폴더에 **GeoJSON(WGS84)** 이 자동 생성됩니다.

- 저장 위치: `seongsu_lt-c-spbd_{timestamp}.geojson`, `seongsu_lt-c-landinfobasemap_{timestamp}.geojson`
- 좌표계: EPSG:3857 → EPSG:4326 변환 (pyproj 사용)

수동 변환이 필요할 때는 `convert_json_to_geojson.py`를 사용할 수 있습니다.

```bash
# 디렉토리 내 레이어 JSON 일괄 변환 (summary 제외)
python scripts/vworld/convert_json_to_geojson.py -d data/raw/vworld/vworld_seongsu_YYYYMMDD_HHMMSS

# 단일 파일
python scripts/vworld/convert_json_to_geojson.py seongsu_lt-c-landinfobasemap_YYYYMMDD_HHMMSS.json -o 출력.geojson
```

## 성수동 좌표 범위

- **경도**: 127.03° ~ 127.08°
- **위도**: 37.53° ~ 37.56°
- **좌표계**: EPSG:4326 (WGS84) → EPSG:3857 (Web Mercator) 변환

## 제약사항 및 고려사항

### 1. bbox 면적 제한

- VWorld API는 **10km² 이내**의 bbox만 지원
- 초과 시 `INVALID_RANGE` 오류 발생
- 스크립트는 자동으로 타일을 분할하여 이 제한을 준수

### 2. API 요청 제한

- 과도한 요청을 방지하기 위해 요청 간 지연 시간 설정 (기본: 0.5초)
- 필요시 `--delay` 옵션으로 조정 가능

### 3. 토지·건물 모두 WFS로 수집

- **LX맵(토지)**·**도로명주소건물(건물)** 모두 **Data API가 아닌 WFS API**로 요청
- WFS의 `PROPERTYNAME`으로 pnu 등 필요한 속성을 명시해 수집
- 타일당 **max_features** 상한(기본 10,000건)으로 한 번에 수집됨. 한 타일 내 피처가 10,000건을 넘으면 초과분은 잘릴 수 있음

### 4. 페이지네이션

- 여기서 사용하는 토지·건물 레이어는 WFS만 사용하므로 **페이지네이션 없이** 타일당 1회 요청
- 다른 레이어를 추가할 경우 Data API 페이지네이션으로 수집 가능

### 5. 좌표계

- VWorld API는 EPSG:3857 (Web Mercator) 사용
- 스크립트는 WGS84 좌표를 자동으로 변환

## 환경 변수

`.env` 파일에 다음 변수가 설정되어 있어야 합니다:

```env
VWORLD_API_KEY=your_api_key_here
vworld_domain=http://localhost
```

## 의존성

- `pyproj`: 좌표 변환 (선택사항, 없으면 근사 변환 사용)
- `requests`: HTTP 요청
- `python-dotenv`: 환경 변수 로드

## 예상 수집 시간

- 성수동 전체 영역: 약 2-4개 타일
- 각 타일당 약 1-2분 (레이어당)
- 전체 수집 시간: 약 5-15분 (네트워크 상태에 따라 다름)

## 문제 해결

### INCORRECT_KEY 오류

- `.env` 파일의 `VWORLD_API_KEY`와 `vworld_domain` 확인
- vworld 개발자센터에서 키 상태 및 등록 도메인 확인

### INVALID_RANGE 오류

- 타일 크기를 더 작게 조정 (`--tile-size 2000`)

### 타임아웃 오류

- `--delay` 값을 증가시켜 요청 간 지연 시간 늘리기
- 네트워크 상태 확인

## 참고 자료

- [VWorld WFS 2.0 마이그레이션 가이드](../../docs/sources/vworld/WFS_2.0/MIGRATION_GUIDE.md)
- [VWorld WFS 2.0 빠른 시작](../../docs/sources/vworld/WFS_2.0/QUICK_START.md)
- [VWorld WFS 컬럼 정보](../../docs/sources/vworld/WFS_2.0/브이월드_WFS_컬럼정보.csv)
