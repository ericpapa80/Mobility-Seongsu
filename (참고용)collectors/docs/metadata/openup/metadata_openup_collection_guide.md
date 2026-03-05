# OpenUp 데이터 수집 가이드 및 메타데이터

## 개요

이 문서는 OpenUp API를 활용한 데이터 수집 시스템의 전체적인 구조, 토큰 관리, 수집 프로세스, 파싱 및 저장 방법을 종합적으로 설명합니다.

---

## 1. 토큰 관리

### 1.1 Access-Token (인증 토큰)

#### 특성
- **변경 가능**: Access-token은 **주기적으로 갱신**됩니다.
- **용도**: OpenUp API 인증에 사용됩니다.
- **형식**: UUID 형식 (예: `5e82f2e6-5300-4e06-af37-e9c5920cda57`)

#### 저장 위치
```
collectors/docs/sources/openup/raw/{날짜}_token
```

**예시 파일:**
- `260113_token`: 2026년 1월 13일 토큰 (서울시 전체 및 경기도 일부)
- `260113_token_mokdong`: 2026년 1월 13일 토큰 (목동 지역)

#### 파일 형식
```text
# 20260113 
# access-token 
OPENUP_ACCESS_TOKEN = 5e82f2e6-5300-4e06-af37-e9c5920cda57

# cell_tokens
  "357b6204",
  "357b626f",
  ...
```

#### 토큰 수집 방법

크롤링을 위해 F12 개발자 도구의 Network 콘솔을 사용하여 토큰을 수집합니다:

1. **Access-Token 수집**:
   - 브라우저에서 F12를 눌러 개발자 도구 열기
   - Network 탭 선택
   - OpenUp 웹사이트에서 특정 건물 클릭
   - Network 탭에서 `create` 요청 찾기
   - `create` 요청의 **Headers** 탭에서 `access-token` 값 확인 및 복사

2. **Cell-Tokens (Hashkeys) 수집**:
   - Network 탭에서 `gp` 요청 찾기
   - `gp` 요청의 **Payload** 탭 열기
   - `hashkeys` 필드에서 값 확인
   - `hashkeys` 값에 마우스 우클릭 → **Copy value** 선택하여 복사

3. **토큰 파일 생성**:
   - 수집한 토큰들을 `D:\VSCODE_PJT\html_of_infinite-ver3\framework\collectors\docs\sources\openup\raw\` 디렉토리에 저장
   - 파일명 형식: `{YYYYMMDD}_token` 또는 `{YYYYMMDD}_token_{지역명}`

**토큰 파일 형식 예시:**
```text
# 20260113 
# access-token 
OPENUP_ACCESS_TOKEN = 5e82f2e6-5300-4e06-af37-e9c5920cda57

# cell_tokens (hashkeys)
  "357b6204",
  "357b626f",
  "357b62ed",
  ...
```

#### 토큰 갱신 시 업데이트 방법
1. 위의 토큰 수집 방법을 따라 새로운 토큰 수집
2. 새로운 토큰 파일을 `collectors/docs/sources/openup/raw/` 디렉토리에 저장
3. 파일명 형식: `{YYYYMMDD}_token` 또는 `{YYYYMMDD}_token_{지역명}`
4. 수집 스크립트 실행 시 `--token-file` 옵션으로 토큰 파일 지정

**예시:**
```bash
# 기본 토큰 파일 사용
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py

# 특정 토큰 파일 사용
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py --token-file 260113_token_mokdong
```

### 1.2 Cell-Tokens (지역 토큰)

#### 특성
- **변경 불가**: Cell-tokens은 **지역을 나타내는 고정 값**으로 변경되지 않습니다.
- **용도**: 특정 지역의 건물 목록을 조회하는 데 사용됩니다.
- **형식**: 16진수 문자열 (8자리, 예: `"357b6204"`)

#### 저장 위치
Access-token과 동일한 파일에 함께 저장됩니다:
```
collectors/docs/sources/openup/raw/{날짜}_token
```

#### Cell-Tokens 예시
- **서울시 전체 및 경기도 일부**: 약 550개 cell-tokens
- **목동 지역**: 10개 cell-tokens
- **성수동 지역**: 13개 cell-tokens

#### Cell-Tokens 로드 방법
수집 스크립트(`collect_seongsu_hash_to_sales.py`)는 토큰 파일에서 자동으로 cell-tokens를 추출합니다:

```python
def load_tokens_from_file(token_filename='260113_token'):
    """토큰 파일에서 access-token과 cell_tokens를 로드."""
    token_file = project_root / "docs" / "sources" / "openup" / "raw" / token_filename
    content = token_file.read_text(encoding='utf-8')
    
    # access-token 추출
    access_token_match = re.search(r'OPENUP_ACCESS_TOKEN\s*=\s*([a-f0-9-]+)', content)
    access_token = access_token_match.group(1) if access_token_match else None
    
    # cell_tokens 추출 (중복 제거)
    tokens = re.findall(r'"([^"]+)"', content)
    unique_tokens = sorted(list(set(tokens)))
    
    return access_token, unique_tokens
```

---

## 2. 데이터 수집 프로세스

### 2.1 수집 스크립트

#### 메인 수집 스크립트
```
collectors/scripts/openup/collect_seongsu_hash_to_sales.py
```

**기능:**
1. 토큰 파일에서 access-token과 cell-tokens 로드
2. 3단계 API 호출을 통한 데이터 수집
3. JSON 및 CSV 형식으로 데이터 저장
4. 병렬 처리로 수집 속도 최적화

#### 주요 옵션
```bash
# 기본 사용 (전체 수집)
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py

# 특정 토큰 파일 사용
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py --token-file 260113_token_mokdong

# 분할 수집 (10등분)
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py --split-index 1

# 테스트 모드 (처음 5개만)
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py --test
```

### 2.2 수집 흐름

#### 1단계: 건물 목록 수집
- **API**: `/v2/pro/bd/hash`
- **입력**: cellTokens 배열
- **출력**: 건물 해시 키 및 기본 정보
- **병렬 처리**: 최대 20개 배치 동시 처리

#### 2단계: 건물별 매장 목록 수집
- **API**: `/v2/pro/bd/sales`
- **입력**: rdnu (건물 해시 키)
- **출력**: 건물 내 매장 storeId 리스트
- **병렬 처리**: 최대 15개 동시 요청

#### 3단계: 매장별 상세 매출 데이터 수집
- **API**: `/v2/pro/store/sales`
- **입력**: storeId
- **출력**: 매장 상세 정보 및 매출 데이터
- **병렬 처리**: 최대 25개 동시 요청

### 2.3 분할 수집

대량의 cell-tokens를 처리하기 위해 분할 수집 기능을 제공합니다:

#### 분할 수집 스크립트
```
collectors/scripts/openup/run_split_collection.ps1
```

**사용 방법:**
```powershell
# 10등분 자동 수집 및 통합
.\collectors\scripts\openup\run_split_collection.ps1
```

**동작 방식:**
1. cell-tokens를 10등분
2. 각 분할을 순차적으로 수집
3. 같은 세션 폴더에 저장
4. 모든 분할 완료 후 자동 통합

---

## 3. 데이터 파싱 및 변환

### 3.1 JSON → Expanded CSV 변환

#### 변환 스크립트
```
collectors/scripts/openup/convert_json_to_expanded_csv.py
```

**기능:**
- JSON 파일의 배열 필드를 개별 컬럼으로 분리
- BI 툴(Power BI, Tableau, Excel)에서 활용하기 쉬운 형식으로 변환

**사용 방법:**
```bash
python collectors/scripts/openup/convert_json_to_expanded_csv.py {JSON파일경로} {출력CSV경로}
```

**변환 예시:**
```json
// 원본 JSON
{
  "salesData": {
    "fam": [60, 0, 42],
    "gender": {
      "f": [0, 6, 25, 0, 11],
      "m": [0, 27, 33, 0, 0]
    }
  }
}
```

```csv
// 변환된 CSV
fam_미혼,fam_기혼,fam_유자녀,gender_f_20대,gender_f_30대,...
60,0,42,0,6,25,0,11,0,27,33,0,0,...
```

### 3.2 Trend 연도별 컬럼 추가

#### 변환 스크립트
```
collectors/scripts/openup/add_trend_yearly_to_csv.py
```

**기능:**
- JSON의 trend 시계열 데이터를 연도별로 집계
- CSV에 연도별 컬럼 추가 (예: `2018_store`, `2018_deli`, `2018_cnt`)

**사용 방법:**
```bash
python collectors/scripts/openup/add_trend_yearly_to_csv.py {JSON파일경로} {CSV파일경로} {출력CSV경로}
```

**추가되는 컬럼:**
- `{연도}_store`: 해당 연도 총 매출 (만원)
- `{연도}_deli`: 해당 연도 배달 매출 (만원)
- `{연도}_cnt`: 해당 연도 매출 건수 (건)

### 3.3 변환 프로세스 예시

목동 데이터를 expanded CSV로 변환하는 전체 프로세스:

```bash
# 1단계: JSON → Expanded CSV
python collectors/scripts/openup/convert_json_to_expanded_csv.py \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong.json \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv

# 2단계: Trend 연도별 컬럼 추가
python collectors/scripts/openup/add_trend_yearly_to_csv.py \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong.json \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv
```

---

## 4. 데이터 저장 구조

### 4.1 저장 위치

#### 기본 저장 경로
```
collectors/data/raw/openup/{timestamp}/
```

**예시:**
```
collectors/data/raw/openup/20260113_151231-목동/
```

#### 분할 수집 저장 경로
```
collectors/data/raw/openup/split_session_{timestamp}/
```

**예시:**
```
collectors/data/raw/openup/split_session_20260113_134457/
├── openup_seoul_gyeonggi_buildings_20260113_134457_split01.json
├── openup_seoul_gyeonggi_buildings_20260113_134457_split01.csv
├── openup_seoul_gyeonggi_stores_20260113_134457_split01.json
├── openup_seoul_gyeonggi_stores_20260113_134457_split01.csv
├── ... (분할 2-10)
└── openup_seoul_gyeonggi_stores_20260113_134457_merged.json (통합 후)
```

### 4.2 저장 파일 형식

#### 건물 데이터
- **JSON**: `openup_seoul_gyeonggi_buildings_{timestamp}.json`
- **CSV**: `openup_seoul_gyeonggi_buildings_{timestamp}.csv`

#### 매장 데이터
- **JSON**: `openup_seoul_gyeonggi_stores_{timestamp}.json`
- **CSV**: `openup_seoul_gyeonggi_stores_{timestamp}.csv`
- **Expanded CSV**: `openup_seoul_gyeonggi_stores_{timestamp}_expanded.csv`

### 4.3 파일 구조 예시

```
collectors/data/raw/openup/20260113_151231-목동/
├── openup_seoul_gyeonggi_buildings_20260113_151231_mokdong.json
├── openup_seoul_gyeonggi_buildings_20260113_151231_mokdong.csv
├── openup_seoul_gyeonggi_stores_20260113_151231_mokdong.json
├── openup_seoul_gyeonggi_stores_20260113_151231_mokdong.csv
└── openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv
```

---

## 5. 데이터 구조

### 5.1 건물 데이터 (Buildings)

#### 파일명
- JSON: `openup_seoul_gyeonggi_buildings_{timestamp}.json`
- CSV: `openup_seoul_gyeonggi_buildings_{timestamp}.csv`

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
      "x": float,
      "y": float,
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

#### 필드 설명

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `building_hash` | string | 건물 고유 해시 키 | `"MqQzQjramex-op"` |
| `road_address` | string | 도로명 주소 | `"서울특별시 성동구 성수이로20길 49"` |
| `address` | string | 지번 주소 | `"서울특별시 성동구 성수동2가 276-3"` |
| `building_names` | array[string] | 건물명 리스트 | `["한양전자산업(주)"]` |
| `decoded_rdnu` | string | 디코딩된 rdnu 값 | `"11200115410934600004900000"` |
| `marker_point` | array[float, float] | 마커 좌표 [경도, 위도] | `[127.0620653, 37.542261]` |
| `center` | array[float, float] | 건물 중심 좌표 [경도, 위도] | `[127.0620653, 37.542261]` |
| `x` | float | 경도 (Longitude) | `127.0620653` |
| `y` | float | 위도 (Latitude) | `37.542261` |
| `geometry` | object | 건물 지오메트리 정보 | `{"type": "Polygon", "coordinates": [...]}` |

#### 메타데이터 필드

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `timestamp` | string | 수집 시각 (YYYYMMDD_HHMMSS 형식) |
| `total_buildings` | int | 수집된 건물 수 |
| `collection_method` | string | 수집 방법 (`"hash_to_sales"`) |
| `cell_tokens_used` | array[string] | 사용된 cellTokens 리스트 |

### 5.2 매장 데이터 (Stores)

#### 파일명
- JSON: `openup_seoul_gyeonggi_stores_{timestamp}.json`
- CSV: `openup_seoul_gyeonggi_stores_{timestamp}.csv`
- Expanded CSV: `openup_seoul_gyeonggi_stores_{timestamp}_expanded.csv`

#### JSON 구조
```json
{
  "data": [
    {
      "storeId": "string",
      "storeNm": "string",
      "road_address": "string",
      "site_address": "string",
      "floor": "string (optional)",
      "category": {
        "bg": "string",
        "mi": "string",
        "sl": "string"
      },
      "coordinates": [float, float],
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

#### 필드 설명

##### 기본 정보

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `storeId` | string | 매장 고유 ID | `"0137207841"` |
| `storeNm` | string | 매장명 | `"성수돈가스"` |
| `road_address` | string | 도로명 주소 | `"서울특별시 성동구 성덕정길 120"` |
| `site_address` | string | 지번 주소 | `"서울 성동구 성수2가1동 574-5번지 2층"` |
| `coordinates` | array[float, float] | 좌표 [경도, 위도] | `[127.0566699, 37.5366923]` |
| `floor` | string (optional) | 층수 정보 | `"1층"`, `"B1"`, `"2층"` (일부 매장에만 존재) |

##### 카테고리 정보 (`category`)

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `bg` | string | 대분류 (업종) | `"음식"`, `"소매"`, `"서비스"` |
| `mi` | string | 중분류 | `"일식"`, `"한식"`, `"패스트푸드"` |
| `sl` | string | 소분류 | `"일식 돈가스 전문점"`, `"버거 전문점"` |

##### 매출 데이터 (`salesData`)

###### 세대별 매출 (`fam`)
- **타입**: `array[int, int, int]`
- **설명**: 10월 건물 세대별 추정 평균 매출 (만원)
- **순서**: `[미혼, 기혼, 유자녀]`
- **예시**: `[102, 4, 30]`

###### 성별/연령대별 매출 (`gender`)
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

###### 소비자 유형별 매출 (`peco`)
- **타입**: `array[int, int, int]`
- **설명**: 10월 건물 소비자 유형별 추정 평균 매출 (만원)
- **순서**: `[개인, 법인, 외국인]`
- **예시**: `[137, 19, 0]`

###### 시간대별 매출 (`times`)
- **타입**: `array[int, int, int, int, int, int, int]`
- **설명**: 10월 건물 시간대별 추정 매출 (만원)
- **순서**: `[아침, 점심, 오후, 저녁, 밤, 심야, 새벽]`
- **예시**: `[0, 41, 37, 0, 25, 51, 0]`

###### 평일/공휴일 매출 (`wdwe`)
- **타입**: `array[int, int]`
- **설명**: 10월 건물 평일/공휴일 추정 평균 매출 (만원)
- **순서**: `[평일, 공휴일]`
- **예시**: `[3, 6]`

###### 재방문 빈도 (`revfreq`)
- **타입**: `array[float, float]`
- **설명**: 재방문 빈도 (평균)
- **순서**: `[평일, 공휴일]`
- **예시**: `[14.3, 14.3]`

###### 요일별 매출 (`weekday`)
- **타입**: `array[int, int, int, int, int, int, int]`
- **설명**: 10월 건물 요일별 추정 평균 매출 (만원)
- **순서**: `[월, 화, 수, 목, 금, 토, 일]`
- **예시**: `[0, 3, 2, 13, 3, 0, 9]`

##### 트렌드 데이터 (`trend`)
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

#### 메타데이터 필드

| 필드명 | 타입 | 설명 |
|--------|------|------|
| `timestamp` | string | 수집 시각 (YYYYMMDD_HHMMSS 형식) |
| `total_stores` | int | 수집된 매장 수 |
| `total_buildings` | int | 수집에 사용된 건물 수 |
| `total_store_ids` | int | 수집된 storeId 수 |
| `collection_method` | string | 수집 방법 (`"hash_to_sales"`) |
| `cell_tokens_used` | array[string] | 사용된 cellTokens 리스트 |

#### Expanded CSV 구조

총 **68개 컬럼**으로 구성:

1. **기본 정보 (9개)**: `storeId`, `storeNm`, `road_address`, `site_address`, `floor`, `category_bg`, `category_mi`, `category_sl`, `x`, `y`
2. **매출 데이터 확장 (35개)**:
   - 세대별: `fam_미혼`, `fam_기혼`, `fam_유자녀`
   - 성별/연령대별: `gender_f_20대` ~ `gender_m_60대` (10개)
   - 소비자 유형: `peco_개인`, `peco_법인`, `peco_외국인`
   - 시간대별: `times_아침` ~ `times_새벽` (7개)
   - 평일/공휴일: `wdwe_평일`, `wdwe_공휴일`
   - 재방문 빈도: `revfreq_평일`, `revfreq_공휴일`
   - 요일별: `weekday_월` ~ `weekday_일` (7개)
3. **연도별 Trend (24개)**: `2018_store`, `2018_deli`, `2018_cnt` ~ `2025_store`, `2025_deli`, `2025_cnt`

자세한 컬럼 설명은 [`metadata_openup_expanded_csv.md`](./metadata_openup_expanded_csv.md)를 참조하세요.

---

## 5.4 제외된 필드

다음 필드들은 수집 시 제외됩니다:

- `cntPng`: 고객 수 데이터 이미지 (Base64 인코딩)
- `salesPng`: 매출 데이터 이미지 (Base64 인코딩)

이 필드들은 파일 크기를 증가시키고 분석에 직접적으로 사용되지 않으므로 제외됩니다.

---

## 5.5 참고 사항

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
- 건물 목록 수집: 최대 20개 배치 동시 처리
- 건물별 매장 목록 조회: 최대 15개 동시 요청
- 매장별 상세 매출 데이터 조회: 최대 25개 동시 요청

---

## 6. 관련 스크립트 및 파일

### 6.1 수집 스크립트
- `collectors/scripts/openup/collect_seongsu_hash_to_sales.py`: 메인 수집 스크립트
- `collectors/scripts/openup/run_split_collection.ps1`: 분할 수집 자동화 스크립트
- `collectors/scripts/openup/merge_split_collections.py`: 분할 수집 파일 통합 스크립트
- `collectors/scripts/openup/monitor_collection.py`: 실시간 수집 모니터링 스크립트

### 6.2 파싱 및 변환 스크립트
- `collectors/scripts/openup/convert_json_to_expanded_csv.py`: JSON → Expanded CSV 변환
- `collectors/scripts/openup/add_trend_yearly_to_csv.py`: Trend 연도별 컬럼 추가

### 6.3 API 클라이언트
- `collectors/plugins/openup/api_client.py`: OpenUp API 클라이언트 구현

### 6.4 설정 파일
- `collectors/config/scrapers/openup.py`: OpenUp 스크래퍼 설정

### 6.5 문서
- `collectors/docs/metadata/openup/metadata_openup.md`: 원본 데이터 구조 설명
- `collectors/docs/metadata/openup/metadata_openup_expanded_csv.md`: Expanded CSV 구조 설명
- `collectors/docs/metadata/openup/metadata_openup_collection_guide.md`: 이 문서 (종합 가이드)
- `collectors/scripts/openup/README.md`: 스크립트 사용 가이드

---

## 7. 주요 특징 및 주의사항

### 7.1 토큰 관리
- ✅ **Access-token은 주기적으로 갱신**되므로 최신 토큰 파일을 사용해야 합니다.
- ✅ **Cell-tokens는 변경되지 않으므로** 한 번 설정하면 계속 사용 가능합니다.
- ✅ 토큰 파일은 `collectors/docs/sources/openup/raw/` 디렉토리에 저장합니다.

### 7.2 수집 최적화
- **병렬 처리**: 건물 목록, 매장 목록, 상세 데이터 수집을 병렬로 처리하여 속도 향상
- **재시도 로직**: API 오류(429, 500, 502, 503, 504) 발생 시 자동 재시도
- **분할 수집**: 대량의 cell-tokens를 10등분하여 순차 수집 후 통합

### 7.3 데이터 품질
- **중복 제거**: cell-tokens에서 중복 자동 제거
- **데이터 검증**: API 응답 유효성 검사 및 오류 처리
- **메타데이터 포함**: 수집 시각, 사용된 토큰, 수집 방법 등 메타데이터 자동 저장

### 7.4 파일 형식
- **JSON**: 원본 데이터 구조 유지, 프로그래밍 분석에 적합
- **CSV**: 기본 데이터, 스프레드시트 분석에 적합
- **Expanded CSV**: 배열 데이터를 개별 컬럼으로 분리, BI 툴 분석에 적합

---

## 8. 사용 예시

### 8.1 기본 수집 (서울시 전체 및 경기도 일부)
```bash
# 1. 토큰 파일 확인
# collectors/docs/sources/openup/raw/260113_token

# 2. 수집 실행
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py

# 3. 결과 확인
# collectors/data/raw/openup/{timestamp}/
```

### 8.2 지역별 수집 (목동)
```bash
# 1. 목동 토큰 파일 사용
python collectors/scripts/openup/collect_seongsu_hash_to_sales.py --token-file 260113_token_mokdong

# 2. 결과 확인
# collectors/data/raw/openup/{timestamp}_mokdong/
```

### 8.3 분할 수집 (대량 데이터)
```powershell
# 1. 분할 수집 자동 실행
.\collectors\scripts\openup\run_split_collection.ps1

# 2. 결과 확인
# collectors/data/raw/openup/split_session_{timestamp}/
```

### 8.4 Expanded CSV 변환
```bash
# 1. JSON → Expanded CSV
python collectors/scripts/openup/convert_json_to_expanded_csv.py \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong.json \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv

# 2. Trend 연도별 컬럼 추가
python collectors/scripts/openup/add_trend_yearly_to_csv.py \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong.json \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv \
  collectors/data/raw/openup/20260113_151231-목동/openup_seoul_gyeonggi_stores_20260113_151231_mokdong_expanded.csv
```

---

## 9. 참고 자료

### 9.1 관련 문서
- [`metadata_openup.md`](./metadata_openup.md): 원본 데이터 구조 상세 설명
- [`metadata_openup_expanded_csv.md`](./metadata_openup_expanded_csv.md): Expanded CSV 컬럼 구조 설명
- [`collectors/scripts/openup/README.md`](../../../scripts/openup/README.md): 스크립트 사용 가이드

### 9.2 API 엔드포인트
- `/v2/pro/bd/hash`: 건물 목록 조회
- `/v2/pro/bd/sales`: 건물별 매장 목록 조회
- `/v2/pro/store/sales`: 매장별 상세 매출 데이터 조회

### 9.3 데이터 출처
- **API 제공**: OpenUp (https://api.openub.com)
- **수집 대상**: 서울시 전체, 경기도 일부, 특정 지역(목동, 성수동 등)
- **수집 방법**: hash → sales(건물) → sales(매장) 흐름

---

## 10. 업데이트 이력

- **2026-01-13**: 종합 메타데이터 문서 작성
  - 토큰 관리 방법 추가
  - 수집 및 파싱 프로세스 설명
  - 저장 구조 및 파일 형식 정리
  - 사용 예시 및 가이드 추가
  - 건물 데이터 필드 설명 추가
  - 매장 데이터 필드 설명 추가
  - 메타데이터 필드 설명 추가
  - 제외된 필드 및 참고 사항 추가
  - F12 개발자 도구를 통한 토큰 수집 방법 추가 (create Headers에서 access-token, gp Payload에서 hashkeys)

---

## 11. 문의 및 지원

토큰 갱신, 수집 오류, 데이터 구조 관련 문의는 프로젝트 관리자에게 연락하시기 바랍니다.
