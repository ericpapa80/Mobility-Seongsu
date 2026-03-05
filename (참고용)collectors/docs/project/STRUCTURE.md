# 프로젝트 구조 문서

## 개요

이 프로젝트는 20~30개 이상의 스크래이퍼 확장을 고려하여 설계된 플러그인 기반 스크래이핑 시스템입니다.

## 폴더 구조

```
all_scrapping/
├── core/                          # 핵심 기능 모듈
│   ├── __init__.py
│   ├── base_scraper.py           # 모든 스크래이퍼의 기본 클래스
│   ├── file_handler.py           # JSON/CSV 파일 처리
│   ├── logger.py                 # 로깅 시스템
│   ├── scraper_registry.py       # 스크래이퍼 레지스트리 및 자동 발견
│   └── runner.py                 # 통합 실행기
│
├── plugins/                       # 스크래이퍼 플러그인 디렉토리
│   ├── __init__.py
│   └── {scraper_name}/            # 각 스크래이퍼는 독립적인 플러그인
│       ├── __init__.py
│       ├── scraper.py            # 스크래이퍼 구현 (필수)
│       ├── api_client.py         # API 클라이언트 (선택)
│       └── config.py             # 플러그인별 설정 (선택)
│
├── config/                        # 설정 관리
│   ├── __init__.py
│   ├── settings.py               # 공통 설정
│   └── scrapers/                 # 스크래이퍼별 설정
│       ├── __init__.py
│       └── {scraper_name}.py     # 각 스크래이퍼의 설정 클래스
│
├── utils/                         # 공통 유틸리티 (레거시, core로 이동 예정)
│   ├── __init__.py
│   ├── auth_manager.py
│   ├── file_handler.py
│   └── logger.py
│
├── scrapers/                      # 레거시 스크래이퍼 (plugins로 마이그레이션 예정)
│   ├── __init__.py
│   ├── base.py
│   └── sgis/
│
├── scripts/                       # 실행 스크립트
│   ├── run_sgis.py               # 레거시 (core.runner 사용 권장)
│   └── scrapers/                  # 스크래이퍼별 개별 스크립트 (선택)
│       └── run_{scraper_name}.py
│
├── data/                          # 수집된 데이터
│   ├── raw/                       # 원본 데이터
│   │   └── {scraper_name}/       # 스크래이퍼별로 자동 생성
│   │       └── {timestamp}/      # 타임스탬프별 디렉토리
│   └── processed/                 # 가공된 데이터
│       └── {scraper_name}/
│
├── logs/                          # 로그 파일
│   └── {scraper_name}/            # 스크래이퍼별 로그 디렉토리
│
├── docs/                          # 문서
│   └── scrapers/                  # 스크래이퍼별 문서
│       ├── README.md              # 플러그인 가이드
│       └── {scraper_name}.md      # 각 스크래이퍼 문서
│
├── .env                           # 환경 변수 (Git에 커밋하지 않음)
├── env_template.txt               # 환경 변수 템플릿
├── requirements.txt               # Python 의존성
├── README.md                       # 프로젝트 메인 문서
└── docs/                          # 문서
    ├── project/                    # 프로젝트 문서
    │   ├── PRD.md                 # 프로젝트 요구사항 문서
    │   └── STRUCTURE.md           # 이 문서
    ├── scrapers/                   # 스크래이퍼 가이드
    └── sources/                    # 출처별 정보
```

## 핵심 개념

### 1. 플러그인 시스템

각 스크래이퍼는 `plugins/` 디렉토리 하위의 독립적인 플러그인으로 구현됩니다. 이는 다음의 장점을 제공합니다:

- **독립성**: 각 스크래이퍼가 완전히 독립적으로 관리됨
- **확장성**: 새로운 스크래이퍼 추가 시 기존 코드 수정 불필요
- **유지보수성**: 각 스크래이퍼의 코드가 분리되어 관리 용이

### 2. 자동 발견 (Auto-discovery)

`ScraperRegistry`가 `plugins/` 디렉토리를 자동으로 스캔하여 사용 가능한 스크래이퍼를 발견하고 등록합니다.

### 3. 통합 실행기

`core.runner` 모듈을 통해 모든 스크래이퍼를 통일된 방식으로 실행할 수 있습니다.

### 4. 설정 분리

각 스크래이퍼의 설정은 `config/scrapers/` 디렉토리에 분리되어 관리됩니다.

## 확장성

이 구조는 다음과 같은 확장을 지원합니다:

1. **수평 확장**: 새로운 스크래이퍼를 `plugins/`에 추가만 하면 됨
2. **수직 확장**: 각 스크래이퍼 내부에서 복잡한 로직 구현 가능
3. **설정 확장**: 스크래이퍼별 독립적인 설정 관리
4. **문서 확장**: 스크래이퍼별 문서화 체계

## 마이그레이션 가이드

기존 `scrapers/` 디렉토리의 스크래이퍼는 `plugins/`로 마이그레이션해야 합니다:

1. `scrapers/{name}/` → `plugins/{name}/`
2. `scrapers.base` → `core.base_scraper`
3. `utils.*` → `core.*`
4. 설정을 `config/scrapers/{name}.py`로 분리

## 사용 예제

```python
# 통합 실행기 사용
python -m core.runner list                    # 모든 스크래이퍼 목록
python -m core.runner run sgis                # SGIS 실행
python -m core.runner run sgis publicdata     # 여러 스크래이퍼 실행

# 프로그래밍 방식
from core.scraper_registry import registry
from core.runner import ScraperRunner

runner = ScraperRunner()
result = runner.run_scraper("sgis")
```

## 향후 개선 사항

1. 스크래이퍼 메타데이터 자동 추출
2. 스크래이퍼 의존성 관리
3. 스크래이퍼 버전 관리
4. 스크래이퍼 테스트 프레임워크
5. 스크래이퍼 성능 모니터링

