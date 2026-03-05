# OpenUp 성수동 데이터 수집 메타데이터

## 개요

이 문서는 `scripts/openup/collect_seongsu_hash_to_sales.py` 스크립트를 통해 수집되는 OpenUp 성수동 데이터의 구조와 각 필드의 의미를 설명합니다.

## 수집 방법

### API 호출 흐름
1. **`/v2/pro/bd/hash`**: cellTokens로 건물 목록 조회
2. **`/v2/pro/bd/sales`**: rdnu(건물 해시 키)로 건물별 매장 목록 조회
3. **`/v2/pro/store/sales`**: storeId로 매장별 상세 매출 데이터 조회

### 저장 파일 구조

수집된 데이터는 다음 파일들로 저장됩니다:

```
data/raw/openup/{timestamp}/
├── openup_seongsu_buildings_{timestamp}.json  # 건물 데이터
├── openup_seongsu_buildings_{timestamp}.csv   # 건물 데이터 (CSV)
├── openup_seongsu_stores_{timestamp}.json     # 매장 데이터
└── openup_seongsu_stores_{timestamp}.csv      # 매장 데이터 (CSV)
```

---

## 건물 데이터 (Buildings)

### 파일명
- JSON: `openup_seongsu_buildings_{timestamp}.json`
- CSV: `openup_seongsu_buildings_{timestamp}.csv`

### 데이터 구조

#### JSON 구조
```json
{
  "data": [
    {
      "building_hash": "string",
      "road_address": "string",
      "address": "string",
      "building_names": ["string"],
      "decoded_rdnu": "string",
      "marker_point": [float, float],
      "center": [float, float],
      "geometry": {
        "type": "Polygon",
        "coordinates": ["string"]
      }
    }
  ],
  "metadata": {
    "timestamp": "string",
    "total_buildings": int,
    "collection_method": "hash_to_sales",
    "cell_tokens_used": ["string"]
  }
}
```

### 필드 설명

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `building_hash` | string | 건물 고유 해시 키 | `"MqQzQjramex-op"` |
| `road_address` | string | 도로명 주소 | `"서울특별시 성동구 성수이로20길 49"` |
| `address` | string | 지번 주소 | `"서울특별시 성동구 성수동2가 276-3"` |
| `building_names` | array[string] | 건물명 리스트 | `["한양전자산업(주)"]` |
| `decoded_rdnu` | string | 디코딩된 rdnu 값 | `"11200115410934600004900000"` |
| `marker_point` | array[float, float] | 마커 좌표 [경도, 위도] | `[127.0620653, 37.542261]` |
| `center` | array[float, float] | 건물 중심 좌표 [경도, 위도] | `[127.0620653, 37.542261]` |
| `geometry` | object | 건물 지오메트리 정보 | `{"type": "Polygon", "coordinates": [...]}` |

### 메타데이터 필드

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `timestamp` | string | 수집 시각 (YYYYMMDD_HHMMSS) |
| `total_buildings` | int | 수집된 건물 수 |
| `collection_method` | string | 수집 방법 (`"hash_to_sales"`) |
| `cell_tokens_used` | array[string] | 사용된 cellTokens 리스트 |

---

## 매장 데이터 (Stores)

### 파일명
- JSON: `openup_seongsu_stores_{timestamp}.json`
- CSV: `openup_seongsu_stores_{timestamp}.csv`

### 데이터 구조

#### JSON 구조
```json
{
  "data": [
    {
      "storeId": "string",
      "category": {
        "bg": "string",
        "mi": "string",
        "sl": "string"
      },
      "storeNm": "string",
      "road_address": "string",
      "site_address": "string",
      "coordinates": [float, float],
      "floor": "string (optional)",
      "salesData": {
        "fam": [int, int, int],
        "gender": {
          "f": [int, int, int, int, int],
          "m": [int, int, int, int, int]
        },
        "peco": [int, int, int],
        "times": [int, int, int, int, int, int, int],
        "wdwe": [int, int],
        "revfreq": [float, float],
        "weekday": [int, int, int, int, int, int, int]
      },
      "trend": [
        {
          "date": "string",
          "store": int,
          "delivery": int,
          "cnt": int
        }
      ]
    }
  ],
  "metadata": {
    "timestamp": "string",
    "total_stores": int,
    "total_buildings": int,
    "total_store_ids": int,
    "collection_method": "hash_to_sales",
    "cell_tokens_used": ["string"]
  }
}
```

### 필드 설명

#### 기본 정보

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `storeId` | string | 매장 고유 ID | `"0137207841"` |
| `storeNm` | string | 매장명 | `"성수돈가스"` |
| `road_address` | string | 도로명 주소 | `"서울특별시 성동구 성덕정길 120"` |
| `site_address` | string | 지번 주소 | `"서울 성동구 성수2가1동 574-5번지 2층"` |
| `coordinates` | array[float, float] | 좌표 [경도, 위도] | `[127.0566699, 37.5366923]` |
| `floor` | string (optional) | 층수 정보 | `"1층"`, `"B1"`, `"2층"` (일부 매장에만 존재) |
| `floor` | string (optional) | 층수 정보 | `"1층"`, `"B1"`, `"2층"` |

#### 카테고리 정보 (`category`)

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `bg` | string | 대분류 (업종) | `"음식"`, `"소매"`, `"서비스"` |
| `mi` | string | 중분류 | `"일식"`, `"한식"`, `"패스트푸드"` |
| `sl` | string | 소분류 | `"일식 돈가스 전문점"`, `"버거 전문점"` |

#### 매출 데이터 (`salesData`)

##### 세대별 매출 (`fam`)
- **타입**: `array[int, int, int]`
- **설명**: 10월 건물 세대별 추정 평균 매출 (만원)
- **순서**: `[미혼, 기혼, 유자녀]`
- **예시**: `[102, 4, 30]`

##### 성별/연령대별 매출 (`gender`)
- **타입**: `object`
- **설명**: 10월 건물 성별/연령대별 추정 평균 매출 (만원)
- **구조**:
  - `f`: 여성 `[20대, 30대, 40대, 50대, 60대]`
  - `m`: 남성 `[20대, 30대, 40대, 50대, 60대]`
- **예시**: 
  ```json
  {
    "f": [67, 4, 10, 0, 0],
    "m": [15, 0, 19, 7, 12]
  }
  ```

##### 소비자 유형별 매출 (`peco`)
- **타입**: `array[int, int, int]`
- **설명**: 10월 건물 소비자 유형별 추정 평균 매출 (만원)
- **순서**: `[개인, 법인, 외국인]`
- **예시**: `[137, 19, 0]`

##### 시간대별 매출 (`times`)
- **타입**: `array[int, int, int, int, int, int, int]`
- **설명**: 10월 건물 시간대별 추정 매출 (만원)
- **순서**: `[아침, 점심, 오후, 저녁, 밤, 심야, 새벽]`
- **예시**: `[0, 41, 37, 0, 25, 51, 0]`

##### 평일/공휴일 매출 (`wdwe`)
- **타입**: `array[int, int]`
- **설명**: 10월 건물 평일/공휴일 추정 평균 매출 (만원)
- **순서**: `[평일, 공휴일]`
- **예시**: `[3, 6]`

##### 재방문 빈도 (`revfreq`)
- **타입**: `array[float, float]`
- **설명**: 재방문 빈도 (평균)
- **순서**: `[평일, 공휴일]`
- **예시**: `[14.3, 14.3]`

##### 요일별 매출 (`weekday`)
- **타입**: `array[int, int, int, int, int, int, int]`
- **설명**: 10월 건물 요일별 추정 평균 매출 (만원)
- **순서**: `[월, 화, 수, 목, 금, 토, 일]`
- **예시**: `[0, 3, 2, 13, 3, 0, 9]`

#### 트렌드 데이터 (`trend`)
- **타입**: `array[object]`
- **설명**: 건물 추정 매출 그래프 데이터 (시계열)
- **구조**:
  ```json
  {
    "date": "string",      // 년월 (YYYYMM 형식)
    "store": int,          // 총합 매출 (만원)
    "delivery": int,       // 배달 매출 (만원)
    "cnt": int             // 매출 건수 (건)
  }
  ```
- **참고**: `store / cnt` = 건당 평균 매출 (만원)
- **예시**:
  ```json
  {
    "date": "201806",
    "store": 0,
    "delivery": 0,
    "cnt": 0
  }
  ```

### 메타데이터 필드

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `timestamp` | string | 수집 시각 (YYYYMMDD_HHMMSS) |
| `total_stores` | int | 수집된 매장 수 |
| `total_buildings` | int | 수집에 사용된 건물 수 |
| `total_store_ids` | int | 수집된 storeId 수 |
| `collection_method` | string | 수집 방법 (`"hash_to_sales"`) |
| `cell_tokens_used` | array[string] | 사용된 cellTokens 리스트 |

---

## 제외된 필드

다음 필드들은 수집 시 제외됩니다:

- `cntPng`: 고객 수 데이터 이미지 (Base64 인코딩)
- `salesPng`: 매출 데이터 이미지 (Base64 인코딩)

이 필드들은 파일 크기를 증가시키고 분석에 직접적으로 사용되지 않으므로 제외됩니다.

---

## 데이터 수집 흐름

### 1단계: 건물 목록 수집
- **API**: `/v2/pro/bd/hash`
- **입력**: cellTokens (13개)
- **출력**: 건물 해시 키 및 기본 정보

### 2단계: 건물별 매장 목록 수집
- **API**: `/v2/pro/bd/sales`
- **입력**: rdnu (건물 해시 키)
- **출력**: 건물 내 매장 storeId 리스트

### 3단계: 매장별 상세 매출 데이터 수집
- **API**: `/v2/pro/store/sales`
- **입력**: storeId
- **출력**: 매장 상세 정보 및 매출 데이터

---

## 참고 사항

### 좌표 시스템
- 좌표는 `[경도, 위도]` 형식으로 저장됩니다.
- 경도: 동경 기준 (예: 127.0566699)
- 위도: 북위 기준 (예: 37.5366923)

### 금액 단위
- 모든 매출 데이터는 **만원** 단위입니다.

### 날짜 형식
- `trend.date`: `YYYYMM` 형식 (예: `"201806"`)
- `metadata.timestamp`: `YYYYMMDD_HHMMSS` 형식 (예: `"20251210_102941"`)

### 병렬 처리
- 건물별 매장 목록 조회: 최대 5개 동시 요청
- 매장별 상세 매출 데이터 조회: 최대 10개 동시 요청

---

## 데이터 출처

- **API 제공**: OpenUp (https://api.openub.com)
- **수집 대상 지역**: 성수동 (서울특별시 성동구)
- **수집 방법**: hash → sales(건물) → sales(매장) 흐름

---

## 업데이트 이력

- 2025-12-10: 초기 메타데이터 문서 작성
  - 건물 데이터 구조 정의
  - 매장 데이터 구조 정의
  - 필드별 상세 설명 추가
