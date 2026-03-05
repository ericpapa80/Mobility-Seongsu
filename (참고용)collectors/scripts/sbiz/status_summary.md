# 시계열 데이터 수집 진행 상황 요약

## 현재 구현된 기능

### ✅ 완료된 작업

1. **시계열 데이터 수집 스크립트** (`collect_timeseries.py`)
   - 날짜별 변경 이력 수집
   - 개폐업일 추적 (chgGb 필드 기반)
   - 중간 저장 기능 (매 30일마다)

2. **데이터 병합 스크립트** (`merge_timeseries.py`)
   - 기본 데이터와 시계열 데이터 병합

3. **성수동 추출 스크립트 개선** (`extract_seongsu.py`)
   - 개폐업일 정보 포함하여 추출

4. **통합 수집 스크립트** (`collect_seongsu_with_timeseries.py`)
   - 전체 프로세스 자동화

5. **API 클라이언트 개선** (`api_client.py`)
   - 페이지네이션 진행 상황 로그 추가 (매 50페이지마다)

### 📊 진행 상황 확인 방법

#### 1. 중간 저장 파일 확인
```bash
# 중간 저장 파일 확인 (매 30일마다 생성)
Get-ChildItem -Path "data\raw\sbiz\timeseries" -Filter "intermediate_*.json" | Sort-Object LastWriteTime -Descending
```

#### 2. 진행 상황 스크립트 실행
```bash
python scripts/sbiz/check_progress.py
```

#### 3. 로그 확인
- 콘솔에 다음 형태로 출력됩니다:
  - `[날짜] 페이지 X/Y (수집된개수/전체개수)`
  - 매 50페이지마다 또는 마지막 페이지에서 출력

### ⚠️ 주의사항

1. **시계열 데이터 수집 시간**
   - 1년치 데이터: 수 시간 소요 가능
   - API 호출 제한: 초당 최대 30 tps
   - 스크립트는 약 20 tps로 제한

2. **중간 저장**
   - 매 30일마다 자동 저장
   - 중단되어도 마지막 중간 저장 지점부터 재개 가능 (구현 필요)

3. **페이지네이션**
   - 특정 날짜에 변경된 업소가 많으면 수백 페이지로 나뉨
   - 예: page 440 = 해당 날짜의 440번째 페이지 (약 44만 개 업소)

### 🔄 다음 단계 (선택사항)

1. **재개 기능 추가**
   - 중간 저장 파일에서 마지막 처리 날짜 확인
   - 해당 날짜부터 재개

2. **진행률 표시 개선**
   - 전체 진행률 계산 및 표시
   - 예상 완료 시간 계산

3. **에러 복구**
   - 특정 날짜 실패 시 재시도 로직
   - 실패한 날짜 목록 저장 및 재처리

## 사용 예시

### 전체 프로세스 실행
```bash
# 최근 1년 데이터 수집
python scripts/sbiz/collect_seongsu_with_timeseries.py --timeseries-days 365
```

### 단계별 실행
```bash
# 1. 기본 데이터 수집
python scripts/sbiz/collect_seongsu.py

# 2. 시계열 데이터 수집
python scripts/sbiz/collect_timeseries.py \
    --start-date 20230101 \
    --end-date 20251202 \
    --target-file data/raw/sbiz/sbiz_stores_dong_성동구_*.json

# 3. 성수동 추출 (개폐업일 포함)
python scripts/sbiz/extract_seongsu.py
```

