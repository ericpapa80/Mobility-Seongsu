# NPS (국민연금공단) 스크래이퍼 문서

## 개요

NPS 스크래이퍼는 국민연금공단에서 제공하는 국민연금 가입 사업장 내역 데이터를 수집하고 처리하는 플러그인입니다.

## 데이터 소스

- **출처**: 국민연금공단 오픈API / 공공데이터포털
- **데이터 형식**: CSV 파일
- **인코딩**: CP949 (EUC-KR)
- **데이터 설명**: 국민연금 가입 사업장의 상세 정보 (주소, 업종, 가입자 수, 급여 정보 등)

## 설치 및 설정

### 필수 패키지

```bash
pip install pandas
```

### 환경 변수 (선택)

```bash
# NPS CSV 파일 경로 (기본값: docs/sources/nps/국민연금공단_국민연금 가입 사업장 내역_20251124.csv)
NPS_CSV_PATH=/path/to/nps_data.csv

# 지오코딩 API 키 (좌표 변환 기능 사용 시 필요)
KAKAO_REST_API_KEY=your_kakao_api_key  # 카카오 로컬 API 키
# 또는
VWORLD_API_KEY=your_vworld_api_key     # Vworld API 키
```

## 사용 방법

### 기본 사용

```python
from plugins.nps.scraper import NPSScraper

scraper = NPSScraper()
result = scraper.scrape(
    filter_address="성수동",
    filter_active_only=True
)
```

### 좌표 추가 (지오코딩)

**상호명(사업장명)과 주소를 함께 활용**하여 더 정확한 x, y 좌표를 자동으로 추가할 수 있습니다:

```python
from plugins.nps.scraper import NPSScraper

scraper = NPSScraper()
result = scraper.scrape(
    filter_address="성수동",
    filter_active_only=True,
    add_coordinates=True,           # 좌표 추가 활성화
    geocoding_service="kakao",      # "kakao" 또는 "vworld"
    geocoding_delay=0.1             # API 호출 간 지연 시간 (초)
)

# 좌표가 포함된 데이터 확인
for record in result['data']['records']:
    if record.get('x') and record.get('y'):
        print(f"{record['사업장명']}: ({record['x']}, {record['y']})")
```

**지오코딩 전략:**
1. **1차 시도**: 주소만으로 검색
2. **2차 시도**: 상호명 + 주소로 키워드 검색 (더 정확)
3. **3차 시도**: 상호명 + 주소를 조합한 주소 검색

이렇게 다단계 전략을 사용하여 지오코딩 성공률과 정확도를 향상시킵니다.

### 성수동 데이터 수집 스크립트

```bash
python scripts/nps/collect_seongsu.py
```

## API 레퍼런스

### NPSScraper

#### `__init__(output_dir: Optional[Path] = None)`

스크래이퍼 초기화

**Parameters:**
- `output_dir`: 데이터 저장 디렉토리 (기본값: `data/`)

#### `scrape(csv_file_path: Optional[str] = None, filter_address: Optional[str] = None, filter_active_only: bool = True, save_json: bool = True, save_csv: bool = True) -> Dict[str, Any]`

국민연금 가입 사업장 데이터 수집

**Parameters:**
- `csv_file_path`: CSV 파일 경로 (기본값: 설정 파일에서 가져옴)
- `filter_address`: 주소 필터 (예: "성수동")
- `filter_active_only`: 활성 사업장만 필터링 (가입상태=1)
- `add_coordinates`: 주소를 좌표로 변환할지 여부 (기본값: False)
- `geocoding_service`: 지오코딩 서비스 ("kakao" 또는 "vworld", 기본값: "kakao")
- `geocoding_delay`: 지오코딩 API 호출 간 지연 시간 (초, 기본값: 0.1)
- `save_json`: JSON 형식으로 저장 여부
- `save_csv`: CSV 형식으로 저장 여부

**Returns:**
- `data`: 수집된 데이터 딕셔너리
- `files`: 저장된 파일 경로들
- `timestamp`: 수집 타임스탬프
- `total_count`: 수집된 레코드 수

**Example:**
```python
scraper = NPSScraper()
result = scraper.scrape(
    filter_address="성수동",
    filter_active_only=True
)
print(f"수집된 사업장 수: {result['total_count']}")
```

#### `find_company(company_name: str, df: Optional[pd.DataFrame] = None) -> pd.DataFrame`

회사명으로 검색

**Parameters:**
- `company_name`: 검색할 회사명
- `df`: 검색할 DataFrame (없으면 먼저 scrape() 호출 필요)

**Returns:**
- 검색 결과 DataFrame

## 데이터 구조

### 원본 데이터 (Raw Data)

CSV 파일의 컬럼 구조:

- `자료생성년월`: 데이터 생성 년월
- `사업장명`: 사업장 이름
- `사업자등록번호`: 사업자 등록번호
- `가입상태`: 가입 상태 (1: 등록, 2: 탈퇴)
- `우편번호`: 우편번호
- `사업장지번상세주소`: 지번 상세 주소
- `주소`: 도로명 주소
- `고객법정동주소코드`: 법정동 주소 코드
- `고객행정동주소코드`: 행정동 주소 코드
- `시도코드`: 시도 코드
- `시군구코드`: 시군구 코드
- `읍면동코드`: 읍면동 코드
- `사업장형태구분코드`: 사업장 형태 (1: 법인, 2: 개인)
- `업종코드`: 업종 코드
- `업종코드명`: 업종 코드명
- `적용일자`: 적용 일자
- `재등록일자`: 재등록 일자
- `탈퇴일자`: 탈퇴 일자
- `가입자수`: 가입자 수
- `금액`: 당월 고지 금액
- `신규`: 신규 취득자 수
- `상실`: 상실 가입자 수

### 가공 데이터 (Processed Data)

정규화된 데이터 구조:

```json
{
  "metadata": {
    "source": "nps",
    "collected_at": "2025-01-01T00:00:00",
    "normalized_at": "2025-01-01T00:00:00",
    "csv_source": "...",
    "filter_address": "성수동",
    "filter_active_only": true,
    "total_count": 100
  },
  "source_specific": {
    "csv_source": "...",
    "filter_address": "성수동",
    "filter_active_only": true,
    "total_count": 100
  },
  "data": {
    "items": [
      {
        "id": "사업자등록번호",
        "name": "사업장명",
                "address": {
          "full": "전체 주소",
          "postal_code": "우편번호",
          "detail": "상세 주소",
          "sido": "시도",
          "administrative_codes": {
            "legal_dong": "법정동 코드",
            "admin_dong": "행정동 코드",
            "sido_code": "시도 코드",
            "sigungu_code": "시군구 코드",
            "eupmyeondong_code": "읍면동 코드"
          }
        },
        "coordinates": {
          "x": 127.0536821,
          "y": 37.5355361,
          "lon": 127.0536821,
          "lat": 37.5355361
        },
        "business": {
          "registration_number": "사업자등록번호",
          "type_code": "사업장형태구분코드",
          "industry_code": "업종코드",
          "industry_name": "업종코드명"
        },
        "pension": {
          "status": "가입상태",
          "members_count": "가입자수",
          "amount": "금액",
          "new_members": "신규",
          "lost_members": "상실",
          "per_person_amount": "인당금액",
          "estimated_monthly_salary": "월급여추정",
          "estimated_annual_salary": "연간급여추정"
        },
        "dates": {
          "application_date": "적용일자",
          "re_registration_date": "재등록일자",
          "withdrawal_date": "탈퇴일자",
          "withdrawal_year": "탈퇴일자_연도",
          "withdrawal_month": "탈퇴일자_월",
          "data_generation_month": "자료생성년월"
        },
        "raw": { /* 원본 데이터 */ }
      }
    ],
    "count": 100
  }
}
```

## 계산 필드

스크래이퍼는 다음 계산 필드를 자동으로 생성합니다:

- `인당금액`: 금액 / 가입자수
- `월급여추정`: 인당금액 / 9 * 100
- `연간급여추정`: 월급여추정 * 12

## 저장 위치

- **원본 데이터**: `data/raw/nps/{timestamp}/`
- **가공 데이터**: `data/processed/nps/{timestamp}/`

## 예제

### 성수동 사업장 데이터 수집

```python
from plugins.nps.scraper import NPSScraper

scraper = NPSScraper()
result = scraper.scrape(
    filter_address="성수동",
    filter_active_only=True
)

print(f"수집된 사업장 수: {result['total_count']}")
print(f"JSON 파일: {result['files']['json']}")
print(f"CSV 파일: {result['files']['csv']}")
```

### 특정 회사 검색

```python
from plugins.nps.scraper import NPSScraper
import pandas as pd

scraper = NPSScraper()
result = scraper.scrape(filter_address="성수동")

# DataFrame으로 변환
df = pd.DataFrame(result['data']['records'])

# 회사 검색
companies = scraper.find_company("카카오", df)
print(companies[['사업장명', '주소', '가입자수', '월급여추정']])
```

## 좌표 추가 기능

### 지오코딩 서비스

NPS 스크래이퍼는 주소를 좌표(x, y)로 변환하는 지오코딩 기능을 지원합니다:

- **카카오 로컬 API** (기본값): 무료 할당량 300,000건/일
- **Vworld API**: 공공데이터, 무료 할당량 제공

### API 키 설정

1. **카카오 로컬 API**:
   - [카카오 개발자 콘솔](https://developers.kakao.com/)에서 애플리케이션 등록
   - REST API 키 발급
   - 환경 변수 설정: `KAKAO_REST_API_KEY=your_key`

2. **Vworld API**:
   - [Vworld 개발자 포털](https://www.vworld.kr/dev/v4api.do)에서 회원가입
   - API 키 발급
   - 환경 변수 설정: `VWORLD_API_KEY=your_key`

### 사용 예제

```python
# 좌표 포함하여 수집
scraper = NPSScraper()
result = scraper.scrape(
    filter_address="성수동",
    add_coordinates=True,
    geocoding_service="kakao",
    geocoding_delay=0.1  # API 호출 간 0.1초 대기 (rate limiting)
)

# 좌표가 추가된 레코드 확인
records_with_coords = [
    r for r in result['data']['records'] 
    if r.get('x') is not None and r.get('y') is not None
]
print(f"좌표가 추가된 사업장: {len(records_with_coords)}개")
```

### 좌표 필드

지오코딩이 성공하면 다음 필드가 추가됩니다:

- `x`: 경도 (longitude)
- `y`: 위도 (latitude)
- `lon`: 경도 별칭
- `lat`: 위도 별칭

좌표는 WGS84 (EPSG:4326) 좌표계를 사용합니다.

## 주의사항

1. CSV 파일은 CP949 인코딩으로 저장되어 있습니다.
2. 데이터 파일이 큰 경우 메모리 사용량이 높을 수 있습니다.
3. 주소 필터는 부분 일치 검색을 수행합니다 (예: "성수동"은 "성수동1가", "성수동2가" 모두 포함).
4. 급여 추정값은 국민연금 고지금액을 기반으로 한 추정치이며 실제 급여와 다를 수 있습니다.
5. 지오코딩 기능 사용 시:
   - API 키가 필요합니다 (카카오 또는 Vworld)
   - 대량 데이터 처리 시 시간이 소요될 수 있습니다
   - API 호출 제한을 고려하여 `geocoding_delay`를 적절히 설정하세요
   - 일부 주소는 지오코딩에 실패할 수 있습니다 (결과에 `x`, `y`가 `None`으로 표시됨)

## 참고 자료

- [국민연금공단 오픈API 가이드](docs/sources/nps/국민연금공단_오픈API활용가이드_국민연금 가입 사업장 내역_v2.0.docx)
- [원본 소스 코드](docs/sources/nps/11-national-pension.py)

