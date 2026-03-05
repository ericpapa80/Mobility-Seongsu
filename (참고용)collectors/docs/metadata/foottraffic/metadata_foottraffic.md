# Foottraffic (골목길 유동인구) 데이터 메타데이터

## 데이터 소스 정보

- **데이터 제공기관**: 서울특별시
- **데이터명**: 골목길 유동인구 데이터
- **데이터 형식**: JSON
- **API 엔드포인트**: `https://golmok.seoul.go.kr/tool/wfs/fpop.json`
- **요청 방식**: POST
- **최신 업데이트**: 2025년 3분기 기준

## 수집 방법

### API 호출 흐름

1. **세션 초기화**: 메인 페이지(`/commercialArea/commercialArea.do`) 방문하여 쿠키 획득
2. **API 호출**: `/tool/wfs/fpop.json` 엔드포인트로 POST 요청
3. **파라미터 전달**: 좌표 범위 및 필터 조건 전달

### 저장 파일 구조

수집된 데이터는 다음 파일들로 저장됩니다:

```
data/raw/foottraffic/foottraffic_seongsu_comprehensive_{timestamp}/
├── foottraffic_seongsu_raw_{timestamp}.json      # 원본 데이터 (중복 포함)
├── foottraffic_seongsu_cleaned_{timestamp}.json   # 정제된 데이터 (중복 제거)
└── foottraffic_seongsu_cleaned_{timestamp}.csv   # 정제된 데이터 (CSV)
```

---

## API 파라미터

### 요청 파라미터

| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| `minx` | float | 최소 X 좌표 (경도) | `204134.2738879806` |
| `miny` | float | 최소 Y 좌표 (위도) | `449887.06429635384` |
| `maxx` | float | 최대 X 좌표 (경도) | `204479.7738879806` |
| `maxy` | float | 최대 Y 좌표 (위도) | `450166.06429635384` |
| `wkt` | string | WKT 형식의 지오메트리 (선택) | `""` (빈 문자열) |
| `dayweek` | integer | 요일 구분 | `1` (주중), `2` (주말) |
| `agrde` | string | 연령대 구분 | `"00"` (전체), `"10"` (10대), `"20"` (20대), `"30"` (30대), `"40"` (40대), `"50"` (50대), `"60"` (60대이상) |
| `tmzon` | string | 시간대 구분 | `"00"` (종일), `"01"` (00~05), `"02"` (06~10), `"03"` (11~13), `"04"` (14~16), `"05"` (17~20), `"06"` (21~23) |
| `ext` | string | 확장 파라미터 | `"ext"` |
| `signguCd` | string | 시군구 코드 | `"11"` (서울특별시) |

### 파라미터 값 상세

#### 요일 구분 (`dayweek`)

| 값 | 설명 |
|---|------|
| `1` | 주중 (평일) |
| `2` | 주말 |

#### 연령대 구분 (`agrde`)

| 값 | 설명 |
|---|------|
| `"00"` | 전체 |
| `"10"` | 10대 |
| `"20"` | 20대 |
| `"30"` | 30대 |
| `"40"` | 40대 |
| `"50"` | 50대 |
| `"60"` | 60대 이상 |

#### 시간대 구분 (`tmzon`)

| 값 | 설명 |
|---|------|
| `"00"` | 종일 |
| `"01"` | 00~05시 |
| `"02"` | 06~10시 |
| `"03"` | 11~13시 |
| `"04"` | 14~16시 |
| `"05"` | 17~20시 |
| `"06"` | 21~23시 |

---

## 원본 데이터 (Raw)

### 파일명
- JSON: `foottraffic_seongsu_raw_{timestamp}.json`

### 데이터 구조

#### JSON 구조
```json
{
  "metadata": {
    "collection_time": "20251223_113909",
    "bounds": {
      "minx": 204134.2738879806,
      "miny": 449887.06429635384,
      "maxx": 204479.7738879806,
      "maxy": 450166.06429635384
    },
    "use_grid": false,
    "grid_size": null,
    "collection_stats": {
      "total_requests": 98,
      "successful_requests": 98,
      "failed_requests": 0,
      "total_records": 4606,
      "unique_roadlinks": 47,
      "combinations": [...]
    },
    "dedup_stats": {
      "total_records": 4606,
      "duplicate_count": 0,
      "unique_count": 4606
    }
  },
  "records": [
    {
      "roadLinkId": "101889",
      "cost": 1631,
      "grade": 5,
      "per": 100,
      "mxcost": 1631,
      "micost": 211,
      "acost": 1631,
      "wkt": "LINESTRING (204369.0 449890.11, 204380.21 449896.98)",
      "_metadata": {
        "dayweek": 1,
        "dayweek_name": "주중",
        "agrde": "00",
        "agrde_name": "전체",
        "tmzon": "00",
        "tmzon_name": "종일",
        "grid_idx": 0,
        "bounds": {...}
      }
    }
  ]
}
```

### 필드 설명

#### 기본 데이터 필드

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `roadLinkId` | string | 도로 링크 고유 ID | `"101889"` |
| `cost` | integer | 유동인구 비용 (점수) | `1631` |
| `grade` | integer | 등급 (1~5) | `5` |
| `per` | float | 백분율 | `100.0` |
| `mxcost` | integer | 최대 비용 | `1631` |
| `micost` | integer | 최소 비용 | `211` |
| `acost` | integer | 평균 비용 | `1631` |
| `wkt` | string | WKT 형식의 지오메트리 (LINESTRING) | `"LINESTRING (204369.0 449890.11, 204380.21 449896.98)"` |

#### 메타데이터 필드 (`_metadata`)

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `dayweek` | integer | 요일 구분 (1: 주중, 2: 주말) |
| `dayweek_name` | string | 요일 이름 |
| `agrde` | string | 연령대 코드 |
| `agrde_name` | string | 연령대 이름 |
| `tmzon` | string | 시간대 코드 |
| `tmzon_name` | string | 시간대 이름 |
| `grid_idx` | integer | 격자 인덱스 (전체 영역 수집 시 0) |
| `bounds` | object | 수집 범위 좌표 |

---

## 정제된 데이터 (Cleaned)

### 파일명
- JSON: `foottraffic_seongsu_cleaned_{timestamp}.json`
- CSV: `foottraffic_seongsu_cleaned_{timestamp}.csv`

### 데이터 구조

#### JSON 구조
```json
{
  "metadata": {
    "collection_time": "20251223_113909",
    "bounds": {...},
    "use_grid": false,
    "total_records": 4606,
    "collection_stats": {...},
    "dedup_stats": {...}
  },
  "records": [
    {
      "roadLinkId": "101889",
      "cost": 1631,
      "grade": 5,
      "per": 100,
      "mxcost": 1631,
      "micost": 211,
      "acost": 1631,
      "wkt": "LINESTRING (204369.0 449890.11, 204380.21 449896.98)",
      "dayweek": 1,
      "dayweek_name": "주중",
      "agrde": "00",
      "agrde_name": "전체",
      "tmzon": "00",
      "tmzon_name": "종일"
    }
  ]
}
```

### 필드 설명

정제된 데이터는 원본 데이터와 동일한 필드를 가지지만, `_metadata` 객체가 제거되고 메타데이터 필드가 일반 필드로 변환됩니다.

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `roadLinkId` | string | 도로 링크 고유 ID |
| `cost` | integer | 유동인구 비용 (점수) |
| `grade` | integer | 등급 (1~5) |
| `per` | float | 백분율 |
| `mxcost` | integer | 최대 비용 |
| `micost` | integer | 최소 비용 |
| `acost` | integer | 평균 비용 |
| `wkt` | string | WKT 형식의 지오메트리 |
| `dayweek` | integer | 요일 구분 (1: 주중, 2: 주말) |
| `dayweek_name` | string | 요일 이름 |
| `agrde` | string | 연령대 코드 |
| `agrde_name` | string | 연령대 이름 |
| `tmzon` | string | 시간대 코드 |
| `tmzon_name` | string | 시간대 이름 |

---

## 중복 제거 로직

### 중복 제거 기준

정제된 데이터는 다음 조합 키를 기준으로 중복을 제거합니다:

- **조합 키**: `roadLinkId + dayweek + agrde + tmzon`

### 중복 처리 방법

같은 조합 키를 가진 레코드가 여러 개인 경우:
- `cost` 값이 가장 높은 레코드만 유지
- 나머지 레코드는 제거

### 주의사항

- 요일/연령대/시간대별로 구분된 데이터는 **별도의 레코드로 유지**됩니다.
- 예를 들어, 같은 `roadLinkId`라도 `dayweek`, `agrde`, `tmzon`이 다르면 다른 레코드로 취급됩니다.

---

## 성수동 좌표 범위

### 기본 좌표 범위 (2025년 3분기 기준)

```json
{
  "minx": 204134.2738879806,
  "miny": 449887.06429635384,
  "maxx": 204479.7738879806,
  "maxy": 450166.06429635384
}
```

### 좌표 시스템

- **좌표계**: UTM-K (한국 좌표계)
- **단위**: 미터 (m)
- **X축**: 경도 방향 (동서)
- **Y축**: 위도 방향 (남북)

---

## 데이터 수집 흐름

### 종합 수집 스크립트

`collect_seongsu_comprehensive.py` 스크립트는 다음 조합으로 데이터를 수집합니다:

1. **요일**: 주중(1), 주말(2)
2. **연령대**: 전체(00), 10대(10), 20대(20), 30대(30), 40대(40), 50대(50), 60대이상(60)
3. **시간대**: 종일(00), 00~05(01), 06~10(02), 11~13(03), 14~16(04), 17~20(05), 21~23(06)

**총 조합 수**: 2 × 7 × 7 = **98개 조합**

### 수집 옵션

- **전체 영역 수집** (기본값): 성수동 전체 영역을 한 번에 수집
- **격자 수집** (`--use-grid`): 영역을 격자로 나누어 순회하며 수집

---

## 데이터 필드 상세 설명

### `cost` (유동인구 비용)

- **의미**: 해당 도로 링크의 유동인구 점수
- **범위**: 양수 정수
- **해석**: 값이 높을수록 유동인구가 많음

### `grade` (등급)

- **의미**: 유동인구 등급
- **범위**: 1~5
- **해석**: 등급이 높을수록 유동인구가 많음

### `per` (백분율)

- **의미**: 해당 시간대/연령대의 유동인구 비율
- **범위**: 0.0 ~ 100.0
- **해석**: 100에 가까울수록 해당 조건에서 유동인구가 많음

### `wkt` (지오메트리)

- **의미**: 도로 링크의 지오메트리 정보 (WKT 형식)
- **타입**: LINESTRING
- **좌표계**: UTM-K (한국 좌표계)
- **예시**: `"LINESTRING (204369.0 449890.11, 204380.21 449896.98)"`

---

## 참고 사항

### API 호출 제한

- API 호출 간 권장 지연 시간: 0.5초 이상
- 세션 유지를 위해 메인 페이지 방문 후 쿠키 획득 필요

### 데이터 제한사항

1. **시간대별 데이터**: 각 시간대별로 별도 조회가 필요합니다.
2. **연령대별 데이터**: 각 연령대별로 별도 조회가 필요합니다.
3. **요일별 데이터**: 주중/주말별로 별도 조회가 필요합니다.

### 좌표 변환

- API는 UTM-K 좌표계를 사용합니다.
- WGS84 (경도/위도) 좌표로 변환이 필요한 경우 별도 변환 작업이 필요합니다.

---

## 데이터 출처

- **API 제공**: 서울특별시 골목길 유동인구 시스템
- **API URL**: https://golmok.seoul.go.kr
- **수집 대상 지역**: 성수동 (서울특별시 성동구)
- **수집 방법**: 종합 수집 스크립트 (`collect_seongsu_comprehensive.py`)

---

## 관련 문서

- [원본 소스 문서](../sources/foottraffic/골목길유동인구_25년%203분기%20기준.txt)
- [수집 스크립트](../../scripts/foottraffic/collect_seongsu_comprehensive.py)
- [스크래퍼 설정](../../config/scrapers/foottraffic.py)

---

## 업데이트 이력

- 2025-12-23: 초기 메타데이터 문서 작성
  - API 파라미터 및 응답 구조 정의
  - 원본/정제 데이터 구조 설명
  - 중복 제거 로직 설명
  - 성수동 좌표 범위 정의

