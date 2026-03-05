# 성수동 전체 매장 수집 가이드

OpenUp API를 활용하여 성수동 전체 매장의 매출 데이터를 수집하기 위한 절차와 준비사항을 정리한 문서입니다.

## 목차

1. [현재 상태 분석](#현재-상태-분석)
2. [성수동 전체 수집 절차](#성수동-전체-수집-절차)
3. [준비사항](#준비사항)
4. [구현 계획](#구현-계획)
5. [대안 방법](#대안-방법)
6. [체크리스트](#체크리스트)

---

## 현재 상태 분석

### 구현된 기능

✅ **좌표 기반 지역 확인** (`/v2/pro/coord`)
- 경계 박스를 사용하여 지역 정보 확인 가능
- 성수동 좌표 범위 확인 완료

✅ **매장별 매출 데이터 수집** (`/v2/pro/store/sales`)
- 매장 ID를 기반으로 상세 매출 데이터 조회 가능
- 7개 매장 테스트 성공

❌ **건물/매장 목록 조회** (`/v2/pro/bd/sales`)
- API 엔드포인트는 확인되었으나 요청 형식 미확인
- 구현 필요

### 현재 제한사항

1. **매장 ID 수동 입력 필요**: 현재는 매장 ID를 직접 제공해야 함
2. **건물 단위 조회 미구현**: 건물 주소나 좌표로 매장 목록을 가져오는 기능 없음
3. **자동 탐색 기능 없음**: 성수동 전체를 자동으로 스캔하는 기능 없음

---

## 성수동 전체 수집 절차

### 1단계: 성수동 영역 정의

성수동은 다음 행정동으로 구성됩니다:
- 성수1가1동
- 성수1가2동
- 성수2가1동
- 성수2가3동

각 동의 좌표 범위를 정의해야 합니다.

```python
SEONGSU_REGIONS = {
    "성수1가1동": {
        "ne": {"lng": 127.055, "lat": 37.555},
        "sw": {"lng": 127.040, "lat": 37.540}
    },
    "성수1가2동": {
        "ne": {"lng": 127.050, "lat": 37.555},
        "sw": {"lng": 127.045, "lat": 37.545}
    },
    "성수2가1동": {
        "ne": {"lng": 127.060, "lat": 37.560},
        "sw": {"lng": 127.050, "lat": 37.550}
    },
    "성수2가3동": {
        "ne": {"lng": 127.065, "lat": 37.565},
        "sw": {"lng": 127.055, "lat": 37.555}
    }
}
```

### 2단계: 매장 목록 확보 방법

#### 방법 A: 건물 단위 API 활용 (건물 목록 확보 필요) ⚠️

OpenUp API의 `/v2/pro/bd/sales` 엔드포인트를 활용하여 건물별 매장 목록을 수집합니다.

**⚠️ 중요 제약사항:**
- OpenUp API에는 **건물 목록을 제공하는 엔드포인트가 없습니다**
- `/v2/pro/bd/sales`는 건물 주소/ID를 **이미 알고 있는 경우**에만 사용 가능
- 따라서 **건물 목록을 다른 소스에서 먼저 확보해야 합니다**

**작동 방식:**
1. **외부 소스에서 성수동 건물 목록 확보** (SBIZ API, 공공데이터 등)
2. 각 건물 주소/ID로 `/v2/pro/bd/sales` API 호출
3. 응답에서 `stores` 배열의 각 항목에서 `storeId` 추출
4. 추출한 `storeId`로 `/v2/pro/store/sales` API 호출하여 상세 매출 데이터 수집

**응답 구조:**
```json
{
    "siteAddr": "서울 성동구 성수동1가...",
    "roadAddr": "서울특별시 성동구 상원1길 26",
    "stores": [
        {
            "storeId": "0134635655",
            "storeNm": "대성갈비",
            "category": {...}
        },
        {
            "storeId": "0123901258",
            "storeNm": "CU 서울숲A타워점",
            ...
        }
    ]
}
```

**필요 작업:**
1. 건물 단위 API 요청 형식 확인 (주소? 좌표? 건물 ID?)
2. 성수동 내 건물 목록 확보
3. 각 건물별 매장 목록 수집 및 `storeId` 추출

#### 방법 B: SBIZ API와 연계

기존 SBIZ API를 활용하여 성수동 매장 목록을 먼저 수집한 후, OpenUp API로 상세 매출 데이터를 조회합니다.

**필요 작업:**
1. SBIZ API로 성수동 매장 목록 수집
2. 매장 ID 매핑 테이블 생성
3. OpenUp API로 매출 데이터 수집

#### 방법 C: 좌표 기반 그리드 탐색

성수동 영역을 작은 그리드로 나누어 각 그리드의 건물/매장을 탐색합니다.

**필요 작업:**
1. 그리드 분할 로직 구현
2. 각 그리드별 건물/매장 탐색
3. 중복 제거 및 통합

### 3단계: 매장 매출 데이터 수집

매장 ID 목록을 확보한 후, 각 매장의 상세 매출 데이터를 수집합니다.

```python
for store_id in store_ids:
    sales_data = api_client.get_store_sales(store_id)
    # 데이터 저장
```

---

## 준비사항

### 1. API 인증 정보

#### Access Token 확인
- 현재 사용 중인 토큰: `295bae90-fbef-492f-9612-4b454f079680` (문서 확인)
- 토큰 유효성 확인 필요
- 필요 시 새 토큰 발급

#### 환경 변수 설정
```bash
# Windows PowerShell
$env:OPENUP_ACCESS_TOKEN="your-access-token-here"

# Linux/Mac
export OPENUP_ACCESS_TOKEN="your-access-token-here"
```

### 2. 성수동 좌표 범위 정확도 향상

현재 사용 중인 좌표는 예시 값입니다. 정확한 좌표 범위를 확보해야 합니다.

**확보 방법:**
- 행정구역 경계 데이터 활용
- 카카오맵/네이버맵 API로 행정동 경계 확인
- 공공데이터포털 행정구역 경계 데이터 활용

### 3. 건물 단위 API 요청 형식 확인 ⚠️

`/v2/pro/bd/sales` API의 정확한 요청 형식을 확인해야 합니다.

**현재 상태:**
- ✅ 응답 구조 확인 완료 (`stores` 배열에 `storeId` 포함)
- ⚠️ Request Payload 형식 미확인 (문서에 명시되지 않음)
- ✅ 인증 필요 확인 (access-token 헤더 필요)

**확인 필요 사항:**
- 요청 파라미터 형식 (주소? 좌표? 건물 ID?)
  - content-length가 25로 매우 짧아 간단한 파라미터일 가능성
  - 예상: `{"bdId": "..."}` 또는 `{"address": "..."}` 형태
- 실제 API 호출 테스트 필요

### 4. 데이터 저장 공간

성수동 전체 매장 수집 시 예상 데이터량:
- 매장 수: 약 500~1000개 (추정)
- 매장당 데이터 크기: 약 15~20KB
- 총 예상 크기: 약 10~20MB (JSON 기준)

**저장 위치:**
- `data/raw/openup/YYYYMMDD_HHMMSS/`
- 충분한 디스크 공간 확보 필요

### 5. API Rate Limiting 대응

**현재 설정:**
- 요청 간 지연: 0.5초
- 예상 소요 시간: 500개 매장 × 0.5초 = 약 4분

**권장 사항:**
- API 제한 정책 확인
- 필요 시 지연 시간 조정
- 배치 처리 구현

---

## 구현 계획

### Phase 1: 건물 단위 API 구현 ✅

**목표:** 건물 주소/좌표로 매장 목록 조회 및 `storeId` 추출

**작업 내용:**
1. `/v2/pro/bd/sales` API 요청 형식 확인
   - 요청 파라미터 확인 (주소? 좌표? 건물 ID?)
   - 실제 API 호출 테스트
2. API 클라이언트 메서드 구현
   - `get_building_sales()` 메서드 완성
   - 응답에서 `storeId` 리스트 추출 로직 추가
3. 테스트 및 검증
   - 성수동 건물 1-2개로 테스트
   - `storeId` 추출 정확도 확인

**예상 기간:** 1-2일

**구현 예시:**
```python
# 건물 단위 API 호출
building_data = api_client.get_building_sales(building_address)

# stores 배열에서 storeId 추출
store_ids = [store['storeId'] for store in building_data.get('stores', [])]

# 각 매장의 상세 매출 데이터 수집
for store_id in store_ids:
    sales_data = api_client.get_store_sales(store_id)
```

### Phase 2: 성수동 건물 목록 확보 ⚠️ (필수)

**목표:** 성수동 내 모든 건물 목록 수집

**⚠️ 중요:** OpenUp API에는 건물 목록 API가 없으므로 외부 소스에서 확보해야 합니다.

**작업 내용:**
1. 성수동 건물 데이터 소스 확보
   - **SBIZ API 활용** (권장)
     - SBIZ API로 성수동 매장 목록 수집
     - 매장 주소에서 건물 정보 추출
     - 건물 단위로 그룹화
   - 공공데이터 활용
     - 행정안전부 건물대장 데이터
     - 국토교통부 건축물대장 데이터
   - 수동 수집 (최후의 수단)
2. 건물 주소/좌표 정리
3. 중복 제거 및 검증
4. OpenUp API 요청 형식에 맞게 변환

**예상 기간:** 2-3일

### Phase 3: 자동 수집 스크립트 구현

**목표:** 성수동 전체 매장 자동 수집

**작업 내용:**
1. 건물 목록 기반 매장 ID 수집
   - 각 건물에 대해 `/v2/pro/bd/sales` API 호출
   - 응답에서 `stores` 배열의 `storeId` 추출
   - 중복 제거 (같은 매장이 여러 건물에 있을 수 있음)
2. 매장별 매출 데이터 수집
   - 추출한 `storeId`로 `/v2/pro/store/sales` API 호출
   - 성수동 필터링 (주소 기반)
3. 진행 상황 모니터링
   - 건물별 진행률 표시
   - 매장별 수집 상태 표시
4. 에러 처리 및 재시도 로직
   - 건물 API 실패 시 재시도
   - 매장 API 실패 시 별도 로그 및 재시도

**예상 기간:** 2-3일

**수집 프로세스:**
```
건물 목록 → 각 건물 API 호출 → stores 배열에서 storeId 추출 
→ 중복 제거 → 각 storeId로 상세 매출 데이터 수집
```

### Phase 4: 데이터 검증 및 정규화

**목표:** 수집된 데이터 품질 보장

**작업 내용:**
1. 데이터 완전성 검증
2. 중복 데이터 제거
3. 데이터 정규화
4. 통계 정보 생성

**예상 기간:** 1-2일

---

## 대안 방법

### 방법 1: 건물 단위 API 활용 (건물 목록 확보 필요) ⚠️

**장점:**
- 매장 ID 자동 추출 가능
- 건물 단위로 체계적 수집
- 응답에 `storeId` 포함 확인됨

**단점:**
- ⚠️ **OpenUp API에 건물 목록 API가 없음**
- 건물 목록을 다른 소스에서 먼저 확보해야 함
- 건물 단위 API 요청 형식 확인 필요 (Request Payload 미확인)

**구현 절차:**
```python
# 1. 성수동 건물 목록 확보
buildings = get_seongsu_buildings()  # 주소 또는 좌표 리스트

# 2. 각 건물별로 매장 목록 조회
all_store_ids = set()
for building in buildings:
    building_data = api_client.get_building_sales(building['address'])
    store_ids = [store['storeId'] for store in building_data.get('stores', [])]
    all_store_ids.update(store_ids)

# 3. 각 매장의 상세 매출 데이터 수집
for store_id in all_store_ids:
    sales_data = api_client.get_store_sales(store_id)
    # 데이터 저장
```

### 방법 2: SBIZ API 연계 활용

**장점:**
- 이미 구현된 SBIZ 스크레이퍼 활용 가능
- 성수동 매장 목록 확보 용이

**단점:**
- SBIZ 매장 ID와 OpenUp 매장 ID 매핑 필요
- 일부 매장은 매핑되지 않을 수 있음

**구현 절차:**
```python
# 1. SBIZ API로 성수동 매장 목록 수집
sbiz_stores = sbiz_scraper.scrape(adong_nm="성수1가1동")

# 2. 매장 정보에서 OpenUp 매장 ID 추출 또는 매핑
# (매장명, 주소 등을 활용하여 매핑)

# 3. OpenUp API로 매출 데이터 수집
for store in sbiz_stores:
    openup_store_id = find_openup_store_id(store)
    if openup_store_id:
        sales_data = openup_client.get_store_sales(openup_store_id)
```

### 방법 3: 좌표 기반 그리드 탐색

**장점:**
- 건물 목록이 없어도 탐색 가능
- 누락 최소화

**단점:**
- 많은 API 호출 필요
- 시간 소요 큼

**구현 절차:**
```python
# 1. 성수동 영역을 작은 그리드로 분할
grid_size = 0.001  # 약 100m 간격
grids = create_grids(seongsu_bbox, grid_size)

# 2. 각 그리드의 중심 좌표로 건물/매장 탐색
for grid in grids:
    buildings = find_buildings_in_grid(grid.center)
    for building in buildings:
        stores = get_building_stores(building)
        store_ids.extend(stores)
```

### 방법 4: 수동 매장 ID 수집

**장점:**
- 구현 간단
- 빠른 시작 가능

**단점:**
- 수동 작업 필요
- 누락 가능성 높음

**구현 절차:**
1. OpenUp 웹사이트에서 성수동 매장 목록 확인
2. 매장 ID 수동 수집
3. 스크립트에 매장 ID 리스트 추가
4. 수집 실행

---

## 체크리스트

### 사전 준비

- [ ] OpenUp API Access Token 확인 및 설정
- [ ] 성수동 정확한 좌표 범위 확보
- [ ] 건물 단위 API 요청 형식 확인
- [ ] 데이터 저장 공간 확인
- [ ] API Rate Limiting 정책 확인

### 구현 단계

- [ ] Phase 1: 건물 단위 API 구현
  - [ ] API 요청 형식 확인
  - [ ] API 클라이언트 메서드 구현
  - [ ] 테스트 및 검증

- [ ] Phase 2: 성수동 건물 목록 확보
  - [ ] 건물 데이터 소스 확보
  - [ ] 건물 주소/좌표 정리
  - [ ] 데이터 검증

- [ ] Phase 3: 자동 수집 스크립트 구현
  - [ ] 건물 기반 매장 ID 수집 로직
  - [ ] 매장별 매출 데이터 수집 로직
  - [ ] 진행 상황 모니터링
  - [ ] 에러 처리 및 재시도

- [ ] Phase 4: 데이터 검증 및 정규화
  - [ ] 데이터 완전성 검증
  - [ ] 중복 제거
  - [ ] 데이터 정규화
  - [ ] 통계 정보 생성

### 테스트 및 검증

- [ ] 소규모 테스트 (10개 매장)
- [ ] 중규모 테스트 (100개 매장)
- [ ] 전체 수집 실행
- [ ] 데이터 품질 검증
- [ ] 누락 매장 확인 및 보완

---

## 예상 소요 시간

| 단계 | 작업 | 예상 시간 |
|------|------|----------|
| Phase 1 | 건물 단위 API 구현 | 1-2일 |
| Phase 2 | 건물 목록 확보 | 2-3일 |
| Phase 3 | 자동 수집 스크립트 | 2-3일 |
| Phase 4 | 데이터 검증 | 1-2일 |
| **총계** | | **6-10일** |

---

## 참고 자료

### 관련 문서
- [OpenUp 스크레이핑 README](../scripts/openup/README.md)
- [SBIZ 스크레이핑 가이드](../scripts/sbiz/README_TIMESERIES.md)

### API 문서
- OpenUp API 문서: `docs/sources/openup/raw/`
- SBIZ API 문서: `docs/sources/sbiz/raw/`

### 코드 참고
- OpenUp 스크레이퍼: `plugins/openup/scraper.py`
- SBIZ 스크레이퍼: `plugins/sbiz/scraper.py`
- 성수동 수집 스크립트: `scripts/openup/collect_seongsu.py`

---

## 문제 해결

### 자주 발생하는 문제

1. **API 토큰 만료**
   - 증상: 401 Unauthorized 에러
   - 해결: 새 토큰 발급 및 환경 변수 업데이트

2. **API Rate Limiting**
   - 증상: 429 Too Many Requests 에러
   - 해결: 요청 간 지연 시간 증가

3. **매장 ID 매핑 실패**
   - 증상: 일부 매장 데이터 누락
   - 해결: 수동 매핑 또는 대안 방법 활용

4. **데이터 불완전**
   - 증상: 일부 필드 누락
   - 해결: 데이터 검증 로직 강화

---

## 다음 단계

1. **건물 목록 확보 방법 결정** (최우선) ⚠️
   - OpenUp API에는 건물 목록 API가 없음
   - SBIZ API 활용 검토 (권장)
   - 공공데이터 활용 검토
   - 수동 수집 방법 검토

2. **건물 단위 API 요청 형식 확인** ⚠️
   - OpenUp API 문서에서 Request Payload 확인
   - 실제 API 호출 테스트
   - 요청 파라미터 확인 (주소? 좌표? 건물 ID?)

2. **성수동 건물 목록 확보** (필수)
   - SBIZ API 활용 검토 (권장)
   - 공공데이터 활용 검토
   - 수동 수집 (필요 시)

3. **자동 수집 스크립트 구현**
   - Phase 1: 건물 단위 API 구현 및 `storeId` 추출
   - Phase 2: 성수동 건물 목록 확보
   - Phase 3: 자동 수집 스크립트 구현

4. **데이터 품질 관리**
   - 검증 로직 구현
   - 모니터링 시스템 구축

## 핵심 발견 사항 ✅

**건물 단위 API 응답 구조:**
- ✅ 응답에 `stores` 배열이 포함됨
- ✅ 각 매장 객체에 `storeId` 필드가 있음
- ⚠️ **하지만 OpenUp API에는 건물 목록을 제공하는 엔드포인트가 없음**

**수집 프로세스 (건물 목록 확보 후):**
```
외부 소스에서 건물 목록 확보 (SBIZ API 등)
   ↓
건물 주소/ID → /v2/pro/bd/sales API 호출 
   ↓
stores 배열에서 storeId 추출 
   ↓
각 storeId로 /v2/pro/store/sales API 호출 
   ↓
상세 매출 데이터 수집
```

**결론:**
- 건물 목록을 다른 소스에서 확보할 수 있다면 이 방식이 효율적입니다
- 건물 목록 확보가 어렵다면 **방법 2 (SBIZ API 연계)** 또는 **방법 3 (좌표 기반 그리드 탐색)**을 고려해야 합니다

---

**작성일:** 2025-12-09  
**최종 수정일:** 2025-12-09  
**작성자:** AI Assistant
