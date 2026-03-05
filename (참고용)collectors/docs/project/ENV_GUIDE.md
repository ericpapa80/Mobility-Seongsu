# 환경 변수 설정 가이드

## 개요

이 프로젝트는 `.env` 파일을 통해 환경 변수를 관리합니다. 각 스크래이퍼의 인증 정보와 설정을 환경 변수로 관리하여 보안을 유지합니다.

## 파일 구조

```
all_scrapping/
├── .env                    # 실제 환경 변수 (Git에 커밋하지 않음)
└── env_template.txt        # 환경 변수 템플릿
```

## 설정 방법

### 1. 템플릿 파일 복사

```bash
# Windows (PowerShell)
Copy-Item env_template.txt .env

# Linux/Mac
cp env_template.txt .env
```

### 2. 실제 값 입력

`.env` 파일을 열어서 각 변수에 실제 값을 입력하세요.

## 환경 변수 구조

### 공통 설정

모든 스크래이퍼에서 공통으로 사용하는 설정입니다.

```env
REQUEST_TIMEOUT=30      # API 요청 타임아웃 (초)
MAX_RETRIES=3          # 최대 재시도 횟수
RETRY_DELAY=1          # 재시도 간격 (초)
```

### 출처별 설정

각 스크래이퍼별로 독립적인 설정을 관리합니다.

#### SGIS 설정

```env
SGIS_CONSUMER_KEY=your_consumer_key_here
SGIS_CONSUMER_SECRET=your_consumer_secret_here
```

#### API Keys

```env
VWORLD_API_KEY=your_vworld_api_key_here
KAKAO_API_KEY=KakaoAK your_kakao_api_key_here
MAPBOX_TOKEN=pk.your_mapbox_token_here
ORS_API_KEY=your_ors_api_key_here
```

#### Database 설정

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

## 새로운 출처 추가 시

새로운 스크래이퍼를 추가할 때는 다음 형식을 따르세요:

```env
# {SOURCE_NAME}_BASE_URL=https://api.example.com
# {SOURCE_NAME}_API_KEY=your_api_key_here
# {SOURCE_NAME}_API_SECRET=your_api_secret_here
```

예시:
```env
PUBLICDATA_BASE_URL=https://www.data.go.kr
PUBLICDATA_API_KEY=your_api_key_here
```

## 보안 주의사항

1. **절대 Git에 커밋하지 마세요**
   - `.env` 파일은 `.gitignore`에 포함되어 있습니다
   - 실수로 커밋하지 않도록 주의하세요

2. **민감한 정보 보호**
   - API 키, 토큰, 비밀번호 등은 절대 공유하지 마세요
   - 팀 내에서도 필요시에만 공유하세요

3. **템플릿 파일 사용**
   - `env_template.txt`는 예시 값만 포함
   - 실제 값은 `.env` 파일에만 저장

## 환경 변수 검증

각 스크래이퍼는 시작 시 환경 변수를 검증합니다:

```python
from config.scrapers.sgis import SGISConfig

if not SGISConfig.validate():
    print("SGIS 설정이 올바르지 않습니다.")
```

## 문제 해결

### 환경 변수가 로드되지 않는 경우

1. `.env` 파일이 프로젝트 루트에 있는지 확인
2. 파일명이 정확히 `.env`인지 확인 (`.env.txt` 아님)
3. 환경 변수 이름이 정확한지 확인 (대소문자 구분)

### 인증 오류가 발생하는 경우

1. `.env` 파일의 토큰/키 값이 올바른지 확인
2. 토큰이 만료되지 않았는지 확인
3. 환경 변수 이름이 코드와 일치하는지 확인

## 참고

- [env_template.txt](../../env_template.txt): 환경 변수 템플릿
- [설정 관리 코드](../config/settings.py): 환경 변수 로드 로직

