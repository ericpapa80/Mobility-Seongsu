# OpenUp 성수동 스크레이핑

OpenUp API를 활용한 성수동 매장 매출 데이터 수집 스크립트입니다.

## 기능

1. **건물 목록 조회**: cellTokens를 사용하여 성수동 건물 목록 조회 (`/v2/pro/bd/hash`)
2. **건물별 매장 목록 조회**: 건물 해시 키(rdnu)를 사용하여 건물별 매장 목록 조회 (`/v2/pro/bd/sales`)
3. **매장 상세 매출 데이터 수집**: 각 매장의 매출액, 방문자 수 등 상세 데이터 수집 (`/v2/pro/store/sales`)
4. **병렬 처리**: 건물별 매장 목록 조회와 매장별 상세 데이터 조회를 병렬로 처리하여 성능 최적화

## 설정

### 환경 변수 설정

OpenUp API 접근을 위한 access-token을 환경 변수로 설정해야 합니다:

```bash
# Windows PowerShell
$env:OPENUP_ACCESS_TOKEN="your-access-token-here"

# Linux/Mac
export OPENUP_ACCESS_TOKEN="your-access-token-here"
```

또는 `.env` 파일에 추가:
```
OPENUP_ACCESS_TOKEN=your-access-token-here
```

### 기본 토큰

문서에서 확인된 기본 토큰이 `config/scrapers/openup.py`에 하드코딩되어 있지만,
실제 사용 시에는 환경 변수로 설정하는 것을 권장합니다.

## 사용 방법

### 기본 사용

```bash
python scripts/openup/collect_seongsu_hash_to_sales.py
```

### 수집 흐름

스크립트는 다음 3단계로 데이터를 수집합니다:

1. **건물 목록 수집**: cellTokens를 사용하여 성수동 건물 목록 조회
2. **매장 ID 수집**: 각 건물의 rdnu를 사용하여 매장 ID 목록 추출
3. **매장 상세 데이터 수집**: 추출한 매장 ID로 상세 매출 데이터 수집

### cellTokens 설정

성수동 전체를 커버하는 13개의 cellTokens가 스크립트에 하드코딩되어 있습니다:

```python
SEONGSU_CELL_TOKENS = [
    "357ca48c", "357ca4f3", "357ca4cf", "357ca4bc", "357ca4c9",
    "357ca4ec", "357ca4c3", "357ca4c5", "357ca47d", "357ca4d1",
    "357ca4db", "357ca4dd", "357ca4e7"
]
```

## API 엔드포인트

### 1. 건물 목록 조회 (`/v2/pro/bd/hash`)

cellTokens를 사용하여 건물 목록을 조회합니다.

```python
payload = {"cellTokens": ["357ca48c", "357ca4f3", ...]}
response = {
    "MqQzQjramex-op": {
        "ROAD_ADDR": "서울특별시 성동구 성수이로20길 49",
        "ADDR": "서울특별시 성동구 성수동2가 276-3",
        "bd_nms": ["한양전자산업(주)"],
        "markerPoint": [127.0620653, 37.542261],
        "center": [127.0620653, 37.542261],
        "geometry": {...}
    },
    ...
}
```

### 2. 건물별 매장 목록 조회 (`/v2/pro/bd/sales`)

건물 해시 키(rdnu)를 사용하여 건물 내 매장 목록을 조회합니다.

```python
payload = {"rdnu": "MqQzQjramex-op"}
response = {
    "siteAddr": "서울 성동구 성수동1가...",
    "roadAddr": "서울특별시 성동구 상원1길 26",
    "stores": [
        {
            "storeId": "0134635655",
            "storeNm": "대성갈비",
            "category": {...}
        },
        ...
    ]
}
```

### 3. 매장별 상세 매출 데이터 조회 (`/v2/pro/store/sales`)

매장 ID를 기반으로 상세 매출 데이터를 조회합니다.

```python
payload = {"storeId": "0134635655"}
response = {
    "storeId": "0134635655",
    "storeNm": "대성갈비",
    "road_address": "서울특별시 성동구 상원1길 26",
    "salesData": {...},
    "trend": [...]
}
```

## 출력 파일

수집된 데이터는 다음 위치에 저장됩니다:

```
data/raw/openup/{timestamp}/
├── openup_seongsu_buildings_{timestamp}.json  # 건물 데이터
├── openup_seongsu_buildings_{timestamp}.csv   # 건물 데이터 (CSV)
├── openup_seongsu_stores_{timestamp}.json     # 매장 데이터
└── openup_seongsu_stores_{timestamp}.csv      # 매장 데이터 (CSV)
```

건물 데이터와 매장 데이터가 별도 파일로 저장됩니다.

## 데이터 구조

### 매장 매출 데이터 예시

```json
{
    "storeId": "0134635655",
    "storeNm": "대성갈비",
    "road_address": "서울특별시 성동구 상원1길 26",
    "site_address": "서울 성동구 성수동1가 656-591번지 서울숲A타워 101, 102 ,103호",
    "category": {
        "bg": "음식",
        "mi": "한식",
        "sl": "한정식/백반 전문점"
    },
    "coordinates": [127.0484324, 37.5461947],
    "salesData": {
        "fam": [1873, 334, 7188],
        "gender": {
            "f": [247, 390, 425, 1214, 954],
            "m": [457, 663, 1830, 1308, 1905]
        },
        "peco": [9397, 6115, 530.0],
        "times": [0, 6977, 932, 4838, 2764, 0, 0],
        "wdwe": [681, 249],
        "revfreq": [20.2, 10.3],
        "weekday": [548, 359, 307, 334, 1195, 673, 0]
    },
    "trend": [
        {
            "date": "202402",
            "store": 2265,
            "delivery": 0,
            "cnt": 213
        },
        // ... 월별 트렌드 데이터
    ],
    "ym": "202510"
}
```

## 주의사항

1. **API Rate Limiting**: 병렬 처리를 사용하므로 API 제한에 주의하세요. 기본 설정:
   - 건물별 매장 목록 조회: 최대 5개 동시 요청
   - 매장별 상세 데이터 조회: 최대 10개 동시 요청
2. **Access Token**: 스크립트 내에 기본 토큰이 하드코딩되어 있지만, 환경 변수로 설정하는 것을 권장합니다.
3. **성수동 필터링**: 주소 기반으로 성수동 매장만 필터링합니다.
4. **데이터 필드**: `cntPng`와 `salesPng` 필드는 수집 시 제외됩니다 (파일 크기 최적화).
5. **cellTokens**: 성수동 전체를 커버하는 13개의 cellTokens가 사용됩니다.

## 성능 최적화

- **병렬 처리**: 건물별 매장 목록 조회와 매장별 상세 데이터 조회를 병렬로 처리
- **배치 처리**: cellTokens를 배치 단위로 처리하여 효율성 향상
- **필드 제외**: 불필요한 이미지 필드(`cntPng`, `salesPng`) 제외로 파일 크기 최적화

## 참고 자료

- **메타데이터 문서**: `docs/openup/metadata.md` - 수집 데이터의 상세 구조 설명
- **API 클라이언트**: `plugins/openup/api_client.py` - OpenUp API 클라이언트 구현
- **수집 스크립트**: `scripts/openup/collect_seongsu_hash_to_sales.py` - 메인 수집 스크립트
