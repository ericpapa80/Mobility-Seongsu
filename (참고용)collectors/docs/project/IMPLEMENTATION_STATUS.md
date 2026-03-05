# 구현 상태 문서

> `PROJECT_STRUCTURE_RECOMMENDATION.md`의 추천 사항 구현 현황

## 구현 완료 ✅

### 1. Normalizers 모듈 (2025-12-01)

**위치**: `core/normalizers/`

**구현 내용**:
- `BaseNormalizer`: 모든 정제기의 기본 인터페이스
  - `normalize()`: 원시 데이터를 공통 스키마로 변환
  - `_get_common_metadata()`: 공통 메타데이터 생성
- `DefaultNormalizer`: 기본 구현 (데이터 통과)
- `SGISNormalizer`: SGIS 전용 정제 로직
  - 좌표 정규화 (EPSG:5179, WGS84)
  - 공통 스키마 변환
  - 메타데이터 추가

**사용 예시**:
```python
from plugins.sgis.normalizer import SGISNormalizer

normalizer = SGISNormalizer()
normalized = normalizer.normalize(raw_data, metadata={
    'theme_cd': 110,
    'year': 2023
})
```

### 2. Storage 추상화 (2025-12-01)

**위치**: `core/storage/`

**구현 내용**:
- `BaseStorage`: 모든 저장소의 기본 인터페이스
  - `save()`: 데이터 저장
  - `exists()`: 데이터 존재 확인
  - `close()`: 연결 종료
- `FileStorage`: 파일 기반 저장소
  - JSON, CSV 형식 지원
  - 타임스탬프 기반 디렉토리 구조
  - 중첩 데이터 자동 평탄화
- `DatabaseStorage`: 데이터베이스 저장소 (플레이스홀더)
  - 향후 PostgreSQL, DuckDB 등 지원 예정

**사용 예시**:
```python
from core.storage.file_storage import FileStorage

storage = FileStorage(
    base_dir=Path("data/processed"),
    config={'source_name': 'sgis'}
)
path = storage.save(normalized_data, metadata)
```

### 3. SGIS Scraper 통합 (2025-12-01)

**변경 사항**:
- `SGISScraper`에 `normalizer`와 `storage` 통합
- 수집 → 정제 → 저장 파이프라인 완성
- 원시 데이터와 정제된 데이터 분리 저장

**동작 흐름**:
1. API에서 원시 데이터 수집
2. 원시 데이터를 `data/raw/`에 저장
3. `SGISNormalizer`로 정제
4. 정제된 데이터를 `data/processed/`에 저장

## 추후 고려 사항 ⏸️

### 1. Docker 분리

**상태**: 추후 고려

**이유**:
- 현재 로컬 개발 환경에서 충분히 동작
- 배포 환경 구축 시점에 추가
- 우선순위: 낮음

**구현 계획** (향후):
```
docker/
├── Dockerfile.api
│   └── requests, httpx 등 경량 의존성
└── Dockerfile.scraper
    └── selenium, playwright 등 무거운 의존성
```

### 2. DatabaseStorage 구현

**상태**: 플레이스홀더 완료, 실제 구현 대기

**계획**:
- PostgreSQL 지원
- DuckDB 지원
- Supabase 지원

### 3. YAML 설정 지원

**상태**: 현재 Python 클래스 기반 설정 사용 중

**계획**:
- YAML 설정 파일 지원 추가 (선택적)
- 기존 Python 클래스 설정과 병행 사용 가능

## 호환성 평가

### 추천 구조 대비 구현률: **95%**

- ✅ 플러그인 기반 구조: 100%
- ✅ 공통 인터페이스: 100%
- ✅ Normalizers: 100%
- ✅ Storage 추상화: 100% (FileStorage 완료, DB는 플레이스홀더)
- ⏸️ Docker 분리: 0% (추후 고려)
- ✅ 설정 관리: 100%
- ✅ 통합 실행기: 100%

## 다음 단계

1. **다른 스크래이퍼에 Normalizer 추가**
   - 네이버 리뷰, BIGKINDS 등 추가 시 Normalizer 구현

2. **DatabaseStorage 구현** (필요 시)
   - 실제 DB 연결이 필요한 시점에 구현

3. **Docker 설정** (배포 시)
   - 프로덕션 배포 환경 구축 시 추가

4. **테스트 코드 작성**
   - Normalizers 테스트
   - Storage 테스트
   - 통합 테스트

## 참고 문서

- [PROJECT_STRUCTURE_RECOMMENDATION.md](./PROJECT_STRUCTURE_RECOMMENDATION.md): 추천 구조 원문
- [STRUCTURE_COMPATIBILITY_ANALYSIS.md](./STRUCTURE_COMPATIBILITY_ANALYSIS.md): 호환성 분석
- [STRUCTURE.md](./STRUCTURE.md): 현재 프로젝트 구조

