# 성동구 → 성수동 데이터 수집 (개폐업일 정보 포함)

## 개요

성동구 전체 데이터를 수집한 후, 성수동만 추출하여 개폐업일 정보까지 포함하는 통합 수집 프로세스입니다.

## 데이터 수집 프로세스

### 1. 기본 데이터 수집
- **대상**: 성동구 전체 (시군구 코드: 11200)
- **API**: `storeListInDong` (행정동 단위 상가업소 조회)
- **저장 위치**: `data/raw/sbiz/sbiz_stores_dong_성동구_YYYYMMDD_HHMMSS/`

### 2. 시계열 데이터 수집 (개폐업일 추적)
- **API**: `storeListByDate` (수정일자기준 상가업소 조회)
- **기능**: 특정 기간 동안 변경된 업소 추적
- **변경구분 필드**: `chgGb`
  - `C`: 신규 개업 (Create)
  - `U`: 정보 수정 (Update)
  - `D`: 폐업 (Delete)
- **저장 위치**: `data/raw/sbiz/timeseries/`

### 3. 성수동 추출
- **대상 행정동**: 성수1가1동, 성수1가2동, 성수2가1동, 성수2가3동
- **기능**: 기본 데이터 + 시계열 데이터 병합
- **저장 위치**: `data/raw/sbiz/sbiz_stores_seongsu_extracted_YYYYMMDD_HHMMSS/`

## 사용 방법

### 방법 1: 통합 스크립트 사용 (권장)

```bash
# 전체 프로세스 실행 (기본 데이터 수집 + 시계열 데이터 수집 + 성수동 추출)
python scripts/sbiz/collect_seongsu_with_timeseries.py

# 옵션 지정
python scripts/sbiz/collect_seongsu_with_timeseries.py \
    --timeseries-start 20230101 \
    --timeseries-end 20251202 \
    --timeseries-days 365

# 일부 단계만 실행
python scripts/sbiz/collect_seongsu_with_timeseries.py --skip-base  # 기본 데이터 수집 건너뛰기
python scripts/sbiz/collect_seongsu_with_timeseries.py --skip-timeseries  # 시계열 데이터 수집 건너뛰기
```

### 방법 2: 단계별 실행

#### 1단계: 기본 데이터 수집
```bash
python scripts/sbiz/collect_seongsu.py
```

#### 2단계: 시계열 데이터 수집
```bash
# 전체 업소 대상 (시간이 오래 걸림)
python scripts/sbiz/collect_timeseries.py \
    --start-date 20230101 \
    --end-date 20251202

# 특정 업소만 대상 (성수동 추출 후)
python scripts/sbiz/collect_timeseries.py \
    --start-date 20230101 \
    --end-date 20251202 \
    --target-file data/raw/sbiz/sbiz_stores_seongsu_extracted_YYYYMMDD_HHMMSS/sbiz_stores_seongsu_YYYYMMDD_HHMMSS.json
```

#### 3단계: 성수동 추출 (개폐업일 정보 포함)
```bash
python scripts/sbiz/extract_seongsu.py
# 또는 시계열 데이터와 함께
python -c "from scripts.sbiz.extract_seongsu import main; from pathlib import Path; main(Path('data/raw/sbiz/timeseries/timeseries_20230101_20251202_YYYYMMDD_HHMMSS.json'))"
```

#### 4단계: 데이터 병합 (선택)
```bash
python scripts/sbiz/merge_timeseries.py \
    --base data/raw/sbiz/sbiz_stores_dong_성동구_YYYYMMDD_HHMMSS/sbiz_stores_dong_성동구_YYYYMMDD_HHMMSS.json \
    --timeseries data/raw/sbiz/timeseries/timeseries_20230101_20251202_YYYYMMDD_HHMMSS.json \
    --output data/raw/sbiz/merged_data.json
```

## 저장되는 데이터 구조

### JSON 파일 구조

```json
{
  "metadata": {
    "collected_at": "2025-12-02T09:47:35.499631",
    "total_count": 8659,
    "timeseries_merged": true,
    "merged_count": 8659,
    "total_with_open_date": 8500,
    "total_with_close_date": 120
  },
  "stores": [
    {
      "bizesId": "MA010120220800003375",
      "bizesNm": "하나애드",
      "adongNm": "성수1가2동",
      "lon": 127.050345411639,
      "lat": 37.5473989062789,
      "openDate": "20220801",
      "closeDate": null,
      "changeHistory": [
        {
          "date": "20220801",
          "chgGb": "C",
          "description": "신규 개업"
        },
        {
          "date": "20230915",
          "chgGb": "U",
          "description": "정보 수정"
        }
      ]
    }
  ]
}
```

### CSV 파일 구조

기존 필드 + 다음 필드 추가:
- `openDate`: 개업일 (YYYYMMDD 형식)
- `closeDate`: 폐업일 (YYYYMMDD 형식, 폐업하지 않은 경우 null)

## 주의사항

1. **시계열 데이터 수집 시간**
   - 1년치 데이터 수집 시 수 시간 소요 가능
   - API 호출 제한: 초당 최대 30 tps
   - 스크립트는 약 20 tps로 제한하여 안전하게 수집

2. **데이터 갱신 주기**
   - API 문서 기준: 분기별 갱신
   - 시계열 데이터는 매일/매주 정기적으로 수집 권장

3. **개폐업일 정보**
   - `chgGb='C'`인 최초 날짜 → 개업일
   - `chgGb='D'`인 날짜 → 폐업일
   - 시계열 데이터 수집 기간 내에서만 추적 가능

4. **메모리 사용량**
   - 대량의 시계열 데이터 수집 시 메모리 사용량 증가
   - 중간 저장 기능으로 안전하게 처리

## 예시

### 전체 프로세스 실행 (최근 1년 데이터)
```bash
python scripts/sbiz/collect_seongsu_with_timeseries.py --timeseries-days 365
```

### 최근 3개월 데이터만 수집
```bash
python scripts/sbiz/collect_seongsu_with_timeseries.py --timeseries-days 90
```

### 기존 데이터에 시계열 정보만 추가
```bash
# 1. 시계열 데이터 수집
python scripts/sbiz/collect_timeseries.py \
    --start-date 20230101 \
    --end-date 20251202 \
    --target-file data/raw/sbiz/sbiz_stores_seongsu_extracted_YYYYMMDD_HHMMSS/sbiz_stores_seongsu_YYYYMMDD_HHMMSS.json

# 2. 성수동 추출 (시계열 데이터 포함)
python -c "
from scripts.sbiz.extract_seongsu import main
from pathlib import Path
main(Path('data/raw/sbiz/timeseries/timeseries_20230101_20251202_YYYYMMDD_HHMMSS.json'))
"
```

## 파일 구조

```
data/raw/sbiz/
├── sbiz_stores_dong_성동구_YYYYMMDD_HHMMSS/     # 기본 데이터
│   ├── sbiz_stores_dong_성동구_YYYYMMDD_HHMMSS.json
│   └── sbiz_stores_dong_성동구_YYYYMMDD_HHMMSS.csv
├── timeseries/                                   # 시계열 데이터
│   ├── timeseries_20230101_20251202_YYYYMMDD_HHMMSS.json
│   └── intermediate_YYYYMMDD.json              # 중간 저장 파일
└── sbiz_stores_seongsu_extracted_YYYYMMDD_HHMMSS/  # 최종 추출 데이터
    ├── sbiz_stores_seongsu_YYYYMMDD_HHMMSS.json
    └── sbiz_stores_seongsu_YYYYMMDD_HHMMSS.csv
```

