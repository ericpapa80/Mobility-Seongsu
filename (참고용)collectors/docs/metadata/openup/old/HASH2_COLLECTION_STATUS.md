# 성수동 전체 OpenUp 건물 데이터 수집 현황

## 실행 결과 분석

### ✅ 성공한 부분

1. **`/v2/pro/bd/hash` API - 건물 목록 수집**
   - 새로운 access-token (`ff42c207-7967-40fe-89d9-5df14e0de026`) 사용
   - 13개 cellTokens로 **1,079개 건물** 수집 성공
   - 성수동 건물 필터링 가능

### ❌ 실패한 부분

1. **`/v2/pro/bd/sales` API - 건물별 매장 목록 조회**
   - **401 Unauthorized** 오류 지속 발생
   - 건물 해시 키로 매장 목록 조회 불가
   - 토큰 권한 문제 또는 API 엔드포인트 접근 제한 가능성

## 현재 상황

### 수집 가능한 데이터
- ✅ 건물 목록 (주소, 좌표, 건물 해시 키)
- ✅ 건물별 기본 정보 (ROAD_ADDR, ADDR, center, geometry)

### 수집 불가능한 데이터
- ❌ 건물별 매장 목록 (storeId)
- ❌ 건물별 매장별 상세 매출 데이터 (건물 해시 키 기반)

## 해결 방안

### 방법 1: 주소 기반 매칭 (현재 구현)
- 수집된 건물 주소를 기반으로 기존 OpenUp 데이터와 매칭
- 기존 데이터: `data/raw/openup/20251209_161239/openup_seongsu_20251209_161239.json`
- 장점: 즉시 사용 가능
- 단점: 기존 데이터에 없는 건물은 매칭 불가

### 방법 2: `/v2/pro/gp` API 활용
- `[gp].txt` 문서에 따르면 cellTokens를 `hashKeys`로 사용 가능
- 건물별 매출 정보는 제공하지만 매장 ID는 없음
- 건물 해시 키는 추출 가능하나 매장 목록은 여전히 불가

### 방법 3: SBIZ API와 통합
- SBIZ API로 성수동 매장 목록 수집
- 주소 기반으로 OpenUp 건물 데이터와 매칭
- 매칭된 매장의 storeId로 상세 매출 데이터 수집

## 필요한 사항

### 1. `/v2/pro/bd/sales` API 접근 권한
- 현재 토큰으로는 접근 불가
- 새로운 토큰 또는 권한 업그레이드 필요
- OpenUp 지원팀 문의 필요 가능성

### 2. cellToken 생성 방법
- 성수동 전체를 커버하는 cellTokens 목록 필요
- 현재 13개 cellTokens로 1,079개 건물 수집
- 성수동 전체 커버 여부 확인 필요

### 3. 대안 데이터 소스
- 기존 OpenUp 데이터 활용 (주소 기반 매칭)
- SBIZ API와 통합
- 다른 OpenUp API 엔드포인트 탐색

## 수정된 스크립트

`scripts/openup/collect_seongsu_full_with_hash2.py`:
- `/v2/pro/bd/hash`로 건물 목록 수집 ✅
- 주소 기반으로 기존 OpenUp 데이터와 매칭 ✅
- 매칭된 storeId로 상세 매출 데이터 수집 ✅

## 실행 방법

```powershell
cd d:\VSCODE_PJT\all_scrapping
python scripts/openup/collect_seongsu_full_with_hash2.py
```

## 예상 결과

1. **건물 목록**: 1,079개 (이미 수집 완료)
2. **매칭된 storeId**: 기존 데이터와 매칭된 수 (변동)
3. **매출 데이터**: 매칭된 storeId로 수집된 상세 매출 정보

## 다음 단계

1. ✅ 주소 기반 매칭 로직 구현 완료
2. ⏳ 스크립트 실행 및 결과 확인
3. ⏳ 매칭률 분석 및 개선 방안 도출
4. ⏳ `/v2/pro/bd/sales` API 접근 권한 확인 (OpenUp 지원팀 문의)
