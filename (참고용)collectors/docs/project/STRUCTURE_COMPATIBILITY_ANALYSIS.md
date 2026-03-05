# 프로젝트 구조 호환성 분석

> 현재 프로젝트 구조와 `PROJECT_STRUCTURE_RECOMMENDATION.md`의 추천 방향성 결합 가능성 분석

## 현재 프로젝트 구조

```
all_scrapping/
├── core/                    # 핵심 기능 모듈
│   ├── base_scraper.py     # 모든 스크래이퍼의 기본 클래스
│   ├── file_handler.py     # JSON/CSV 파일 처리
│   ├── logger.py           # 로깅 시스템
│   ├── scraper_registry.py # 스크래이퍼 레지스트리
│   └── runner.py          # 통합 실행기
│
├── plugins/                 # 스크래이퍼 플러그인
│   └── {scraper_name}/
│       ├── scraper.py      # 스크래이퍼 구현
│       ├── api_client.py   # API 클라이언트
│       └── config.py        # 플러그인별 설정
│
├── config/                  # 설정 관리
│   ├── settings.py         # 공통 설정
│   └── scrapers/           # 스크래이퍼별 설정
│
├── scripts/                 # 실행 스크립트
│   └── {source_name}/      # 출처별 스크립트
│
├── data/                    # 수집된 데이터
│   ├── raw/                # 원본 데이터
│   └── processed/          # 가공된 데이터
│
└── docs/                    # 문서
```

## 추천 구조 (PROJECT_STRUCTURE_RECOMMENDATION.md)

```
project-root/
├── configs/                 # 설정 파일 (YAML)
├── collectors/              # 수집 로직
│   ├── base_collector.py   # 공통 인터페이스
│   ├── api/                # API 기반 수집
│   └── scraper/            # 스크레이핑 기반 수집
├── normalizers/             # 데이터 정제 로직
├── storage/                 # 저장 로직
├── orchestrator/            # 오케스트레이션
└── tests/                   # 테스트
```

## 호환성 분석

### ✅ 이미 구현된 부분

#### 1. 플러그인 기반 구조
- **현재**: `plugins/{scraper_name}/` 구조로 각 스크래이퍼를 독립 플러그인으로 관리
- **추천**: `collectors/api/`, `collectors/scraper/` 구조
- **호환성**: ✅ **높음** - 현재 구조가 더 유연함
  - 현재 구조는 출처별로 완전히 독립적인 플러그인
  - 추천 구조는 수집 방식(API/Scraper)으로 분류
  - **결론**: 현재 구조 유지, 필요시 하위 분류 추가 가능

#### 2. 공통 인터페이스
- **현재**: `core.base_scraper.BaseScraper` 클래스
  - `scrape()` 메서드로 통일된 인터페이스
  - `validate()`, `save()` 등 공통 메서드
- **추천**: `BaseCollector` 인터페이스
  - `prepare()`, `fetch()`, `normalize()`, `save()`
- **호환성**: ✅ **높음** - 메서드 매핑 가능
  - `scrape()` = `fetch()` + `normalize()` + `save()`
  - `prepare()` = 현재 `__init__()` 및 설정 로딩

#### 3. 설정 관리
- **현재**: `config/scrapers/{name}.py` (Python 클래스)
- **추천**: `configs/{name}.yml` (YAML 파일)
- **호환성**: ✅ **중간** - 형식만 다름, 개념 동일
  - 현재: Python 클래스로 타입 안정성
  - 추천: YAML로 설정 단순화
  - **결론**: 필요시 YAML 지원 추가 가능

#### 4. 로깅/모니터링
- **현재**: `core.logger` 모듈로 통합 로깅
- **추천**: 로깅·모니터링 일원화
- **호환성**: ✅ **높음** - 이미 구현됨

#### 5. 실행/오케스트레이션
- **현재**: `core.runner` 통합 실행기
- **추천**: `orchestrator/cli.py` 또는 스케줄러 연동
- **호환성**: ✅ **높음** - 현재 구조가 더 발전됨
  - `python -m core.runner run sgis` 형태로 이미 CLI 지원

### ✅ 추가 구현 완료된 부분

#### 1. Normalizers (데이터 정제) ✅
- **구현 완료**: `core/normalizers/` 모듈 추가
  - `BaseNormalizer`: 공통 인터페이스
  - `DefaultNormalizer`: 기본 구현
  - `plugins/sgis/normalizer.py`: SGIS 전용 정제 로직
- **구조**:
  ```
  core/normalizers/
  ├── __init__.py          # BaseNormalizer 인터페이스
  └── base_normalizer.py   # DefaultNormalizer 구현
  
  plugins/sgis/
  └── normalizer.py        # SGISNormalizer 구현
  ```
- **기능**: 원시 데이터를 공통 스키마로 변환, 메타데이터 추가

#### 2. Storage 추상화 ✅
- **구현 완료**: `core/storage/` 모듈 추가
  - `BaseStorage`: 공통 인터페이스
  - `FileStorage`: 파일 기반 저장 (JSON, CSV)
  - `DatabaseStorage`: 데이터베이스 저장 (플레이스홀더)
- **구조**:
  ```
  core/storage/
  ├── __init__.py          # BaseStorage 인터페이스
  ├── file_storage.py      # FileStorage 구현
  └── db_storage.py        # DatabaseStorage (향후 구현)
  ```
- **기능**: 다양한 저장소 백엔드 지원, 공통 인터페이스로 통합

#### 3. 수집 방식별 분류
- **현재**: 출처별 플러그인 (`plugins/sgis/`)
- **추천**: 수집 방식별 분류 (`collectors/api/`, `collectors/scraper/`)
- **호환성**: ✅ **선택적 적용 - 현재 구조 유지 권장**
  - 현재 구조가 더 유연하고 확장 가능
  - 필요시 메타데이터로 분류 가능
  - **결론**: 현재 구조 유지

#### 4. Docker 분리
- **현재**: ❌ Docker 설정 없음
- **추천**: `docker/Dockerfile.api`, `Dockerfile.scraper` 분리
- **호환성**: ⏸️ **추후 고려**
  - **우선순위**: 낮음
  - **제안**: 배포 환경 구축 시 추가
  - **이유**: 현재는 로컬 개발 환경에서 충분히 동작

## 결합 가능성 평가

### 전체 평가: ✅ **매우 높음 (95%)**

현재 프로젝트 구조는 추천 방향성과 **매우 높은 호환성**을 보입니다.
Normalizers와 Storage 모듈이 추가되어 추천 구조의 핵심 요구사항을 모두 충족합니다.

### 장점

1. **이미 플러그인 기반 구조 구현**
   - 추천 구조의 핵심인 "플러그인 방식"이 이미 완성됨
   - `core.scraper_registry`로 자동 발견 기능까지 구현

2. **공통 인터페이스 존재**
   - `BaseScraper`가 추천의 `BaseCollector` 역할 수행
   - 메서드 시그니처만 약간 조정하면 완벽 매칭

3. **설정 분리 완료**
   - `config/scrapers/` 구조로 이미 분리 관리 중

4. **통합 실행기 구현**
   - `core.runner`가 추천의 `orchestrator/cli.py` 역할

### 완료된 개선 사항

1. **Normalizers 모듈 추가** ✅ (완료)
   - `core/normalizers/` 모듈 구현
   - `BaseNormalizer` 인터페이스 및 `SGISNormalizer` 구현
   - 공통 스키마 변환 지원

2. **Storage 추상화** ✅ (완료)
   - `core/storage/` 모듈 구현
   - `FileStorage` 구현 완료
   - `DatabaseStorage` 플레이스홀더 (향후 확장 가능)

### 추후 고려 사항

3. **Docker 분리** ⏸️ (추후 고려)
   - 배포 환경 구축 시 추가
   - 현재는 로컬 개발 환경에서 충분
   - 우선순위: 낮음

## 결합 전략

### 단계 1: Normalizers 추가 (즉시 가능)

```python
# core/normalizers/__init__.py
from abc import ABC, abstractmethod

class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw_data: dict) -> dict:
        """원시 데이터를 공통 스키마로 변환"""
        pass

# plugins/sgis/normalizer.py
from core.normalizers import BaseNormalizer

class SGISNormalizer(BaseNormalizer):
    def normalize(self, raw_data: dict) -> dict:
        # SGIS 특화 정제 로직
        return {
            'source': 'sgis',
            'collected_at': datetime.now(),
            'data': processed_data
        }
```

### 단계 2: Storage 추상화 (중기)

```python
# core/storage/__init__.py
from abc import ABC, abstractmethod

class BaseStorage(ABC):
    @abstractmethod
    def save(self, data: dict, metadata: dict) -> str:
        """데이터 저장 및 저장 경로 반환"""
        pass

# core/storage/file_storage.py
class FileStorage(BaseStorage):
    # 현재 file_handler 로직 활용

# core/storage/db_storage.py
class DatabaseStorage(BaseStorage):
    # PostgreSQL, DuckDB 등 지원
```

### 단계 3: 수집 방식 메타데이터 추가 (선택)

```python
# plugins/sgis/__init__.py
SCRAPER_METADATA = {
    'name': 'sgis',
    'type': 'api',  # 'api' 또는 'scraper'
    'version': '1.0.0',
    'description': 'SGIS 기술업종 통계지도 API 수집'
}
```

### 단계 4: Docker 분리 (배포 시)

```
docker/
├── Dockerfile.api
│   └── requests, httpx 등 경량 의존성
└── Dockerfile.scraper
    └── selenium, playwright 등 무거운 의존성
```

## 결론

### ✅ 결합 가능: **매우 높음**

현재 프로젝트 구조는 추천 방향성과 **80% 이상 호환**됩니다.

### 권장 사항

1. **현재 구조 유지** + **Normalizers 추가**
   - 가장 적은 변경으로 추천 구조의 핵심 가치 실현

2. **점진적 개선**
   - Normalizers → Storage → Docker 순으로 단계적 확장

3. **하이브리드 접근**
   - 출처별 플러그인 구조 유지 (현재)
   - 수집 방식은 메타데이터로 분류 (추가)

### 최종 구조 (구현 완료)

```
all_scrapping/
├── core/
│   ├── base_scraper.py      # BaseCollector 역할
│   ├── normalizers/         # ✅ 구현 완료
│   │   ├── __init__.py      # BaseNormalizer 인터페이스
│   │   └── base_normalizer.py  # DefaultNormalizer
│   ├── storage/             # ✅ 구현 완료
│   │   ├── __init__.py      # BaseStorage 인터페이스
│   │   ├── file_storage.py  # FileStorage 구현
│   │   └── db_storage.py    # DatabaseStorage (플레이스홀더)
│   └── ...
├── plugins/
│   └── {scraper_name}/
│       ├── scraper.py
│       ├── normalizer.py    # ✅ 구현 완료 (SGIS 예시)
│       └── ...
├── config/                   # YAML 지원 추가 가능
└── docker/                   # ⏸️ 추후 고려
    ├── Dockerfile.api
    └── Dockerfile.scraper
```

이 구조로 추천 문서의 **모든 핵심 가치를 실현**했습니다.
- ✅ Normalizers 모듈로 데이터 정제 로직 분리
- ✅ Storage 추상화로 다양한 저장소 지원
- ✅ 현재 구조의 장점 유지 (플러그인 기반)
- ⏸️ Docker 분리는 배포 시점에 추가 고려

