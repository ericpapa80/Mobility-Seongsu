# 다중 출처 스크래이핑 시스템

다양한 출처의 웹사이트로부터 데이터를 체계적으로 수집하고, JSON 및 CSV 형식으로 저장하는 확장 가능한 스크래이핑 시스템입니다.

## 주요 기능

- **SGIS 데이터 수집**: 통계지리정보서비스(SGIS) API를 통한 POI 회사 밀도 데이터 수집
- **다중 포맷 저장**: JSON 및 CSV 형식으로 데이터 저장
- **확장 가능한 아키텍처**: 새로운 스크래이퍼 추가 용이
- **인증 관리**: .env 파일을 통한 안전한 인증 정보 관리
- **로깅 시스템**: 구조화된 로깅 시스템

## 프로젝트 구조

이 프로젝트는 **플러그인 기반 구조**로 설계되어 20~30개 이상의 스크래이퍼 확장을 지원합니다.

```
all_scrapping/
├── core/                    # 핵심 기능 모듈
│   ├── base_scraper.py     # 기본 스크래이퍼 클래스
│   ├── file_handler.py     # 파일 처리 (JSON/CSV)
│   ├── logger.py           # 로깅 시스템
│   ├── scraper_registry.py # 스크래이퍼 레지스트리
│   └── runner.py           # 통합 실행기
├── plugins/                 # 스크래이퍼 플러그인
│   └── {scraper_name}/     # 각 스크래이퍼는 독립 플러그인
│       ├── scraper.py      # 스크래이퍼 구현
│       └── api_client.py   # API 클라이언트 (선택)
├── config/                  # 설정 관리
│   ├── settings.py         # 공통 설정
│   └── scrapers/           # 스크래이퍼별 설정
├── data/                    # 수집된 데이터
│   ├── raw/{scraper_name}/ # 스크래이퍼별 자동 생성
│   └── processed/{scraper_name}/
├── logs/{scraper_name}/     # 스크래이퍼별 로그
└── scripts/                 # 실행 스크립트
```

자세한 구조는 [docs/project/STRUCTURE.md](docs/project/STRUCTURE.md)를 참조하세요.

## 설치 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`env_template.txt` 파일을 `.env`로 복사하고 실제 값으로 수정하세요:

```bash
# Windows (PowerShell)
Copy-Item env_template.txt .env

# Linux/Mac
cp env_template.txt .env
```

그 다음 `.env` 파일을 열어서 각 변수에 실제 값을 입력하세요:

```env
# SGIS API
SGIS_CONSUMER_KEY=your_consumer_key_here
SGIS_CONSUMER_SECRET=your_consumer_secret_here

# API Keys
VWORLD_API_KEY=your_vworld_api_key_here
KAKAO_API_KEY=KakaoAK your_kakao_api_key_here
MAPBOX_TOKEN=pk.your_mapbox_token_here
ORS_API_KEY=your_ors_api_key_here

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

**주의**: `.env` 파일은 Git에 커밋하지 마세요. 실제 인증 정보를 입력하세요.

자세한 내용은 [환경 변수 설정 가이드](docs/project/ENV_GUIDE.md)를 참조하세요.

## 사용 방법

### 통합 실행기 사용 (권장)

모든 스크래이퍼 목록 보기:

```bash
python -m core.runner list
```

특정 스크래이퍼 실행:

```bash
python -m core.runner run sgis
```

여러 스크래이퍼 실행:

```bash
python -m core.runner run sgis publicdata weather
```

JSON만 저장:

```bash
python -m core.runner run sgis --json-only
```

출력 디렉토리 지정:

```bash
python -m core.runner run sgis --output-dir /path/to/output
```

### 개별 스크립트 사용 (레거시)

```bash
python scripts/run_sgis.py
```

## 데이터 저장 위치

수집된 데이터는 다음 위치에 저장됩니다:

- **원본 데이터**: `data/raw/sgis/{timestamp}/`
- **가공된 데이터**: `data/processed/sgis/{timestamp}/` (향후 구현)

파일명 형식:
- JSON: `sgis_poi_density_{timestamp}.json`
- CSV: `sgis_poi_density_{timestamp}.csv`

## 새로운 스크래이퍼 추가하기

플러그인 방식으로 새로운 스크래이퍼를 쉽게 추가할 수 있습니다:

1. `plugins/` 디렉토리에 새 폴더 생성: `plugins/my_scraper/`
2. `scraper.py` 파일 생성 및 `BaseScraper` 상속
3. 설정 파일 생성 (선택): `config/scrapers/my_scraper.py`
4. `.env` 파일에 필요한 환경 변수 추가

자세한 가이드는 [docs/scrapers/README.md](docs/scrapers/README.md)를 참조하세요.

## 로깅

로그 파일은 `logs/` 디렉토리에 저장됩니다:
- 파일명 형식: `{logger_name}_{YYYYMMDD}.log`
- 콘솔에도 동시에 출력됩니다

## 기술 스택

- Python 3.8+
- requests: HTTP 요청 처리
- python-dotenv: 환경 변수 관리
- pandas: 데이터 처리
- urllib3: HTTP 클라이언트 유틸리티

## 주의사항

1. **인증 정보 보안**: `.env` 파일에 실제 인증 정보를 저장하되, Git에 커밋하지 마세요.
2. **API 사용 제한**: API 사용 제한이 있을 수 있으므로, 과도한 요청을 피하세요.
3. **데이터 보관**: 수집된 데이터는 적절히 백업하세요.

## 문제 해결

### 인증 오류
- `.env` 파일의 `SGIS_ACCESS_TOKEN`과 `SGIS_JSESSIONID`가 올바른지 확인하세요.
- 토큰이 만료되었을 수 있으므로 새로 발급받으세요.

### 데이터 저장 오류
- `data/` 디렉토리에 쓰기 권한이 있는지 확인하세요.
- 디스크 공간이 충분한지 확인하세요.

## 라이선스

이 프로젝트는 개인 사용 목적으로 제작되었습니다.

## 참고 문서

### 프로젝트 문서
- [PRD 문서](docs/project/PRD.md): 상세한 프로젝트 요구사항 및 아키텍처 문서
- [구조 문서](docs/project/STRUCTURE.md): 프로젝트 구조 상세 설명
- [마이그레이션 가이드](docs/project/MIGRATION_GUIDE.md): 기존 코드 마이그레이션 가이드
- [환경 변수 가이드](docs/project/ENV_GUIDE.md): 환경 변수 설정 및 관리 가이드

### 스크래이퍼 가이드
- [스크래이퍼 플러그인 가이드](docs/scrapers/README.md): 새로운 스크래이퍼 추가 방법

### 출처별 정보
- [SGIS 정보](docs/sources/sgis/sgis.md): SGIS 스크래이핑 사이트 정보

