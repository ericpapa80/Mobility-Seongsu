# NPS 스크래이퍼 환경 변수 설정 가이드

## .env 파일 설정

NPS 스크래이퍼의 지오코딩 기능을 사용하려면 다음 환경 변수를 설정해야 합니다.

### 카카오 로컬 API (권장)

카카오 로컬 API를 사용하여 주소를 좌표로 변환합니다.

#### 1. API 키 발급

1. [카카오 개발자 콘솔](https://developers.kakao.com/) 접속
2. 애플리케이션 등록
3. "앱 키" 메뉴에서 **REST API 키** 복사

#### 2. .env 파일 설정

다음 중 하나의 방법으로 설정할 수 있습니다:

**방법 1: KAKAO_REST_API_KEY 사용 (권장)**
```bash
KAKAO_REST_API_KEY=your_rest_api_key_here
```

**방법 2: 기존 KAKAO_API_KEY 사용**
```bash
# 기존 설정이 있다면 그대로 사용 가능
# "KakaoAK " 접두사는 자동으로 제거됩니다
KAKAO_API_KEY=KakaoAK your_rest_api_key_here
# 또는 접두사 없이
KAKAO_API_KEY=your_rest_api_key_here
```

### Vworld API (대안)

공공데이터 Vworld API를 사용할 수도 있습니다.

#### 1. API 키 발급

1. [Vworld 개발자 포털](https://www.vworld.kr/dev/v4api.do) 접속
2. 회원가입 및 로그인
3. API 키 발급

#### 2. .env 파일 설정

```bash
VWORLD_API_KEY=your_vworld_api_key_here
```

## .env 파일 예시

```bash
# ============================================
# SGIS API
# ============================================
SGIS_CONSUMER_KEY=your_consumer_key_here
SGIS_CONSUMER_SECRET=your_consumer_secret_here

# ============================================
# SBIZ API (소상공인시장진흥공단)
# ============================================
SBIZ_SERVICE_KEY=your_sbiz_service_key_here

# ============================================
# NPS API (국민연금공단)
# ============================================
# SBIZ API를 NPS 데이터 처리에도 활용할 수 있음
SBIZ_SERVICE_KEY=your_sbiz_service_key_here

# ============================================
# NPS 지오코딩 API (국민연금공단 데이터의 좌표 변환용)
# ============================================
# 카카오 로컬 API (권장)
KAKAO_REST_API_KEY=your_kakao_rest_api_key_here
# 또는 기존 KAKAO_API_KEY 사용 가능 (geocoder가 자동으로 인식)
KAKAO_API_KEY=KakaoAK your_kakao_api_key_here

# Vworld API (대안)
VWORLD_API_KEY=your_vworld_api_key_here

# ============================================
# 기타 API Keys
# ============================================
MAPBOX_TOKEN=pk.your_mapbox_token_here
ORS_API_KEY=your_ors_api_key_here

# ============================================
# Database
# ============================================
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

## 현재 .env 파일 확인

현재 설정된 환경 변수 확인:

```python
import os
from pathlib import Path

# .env 파일 로드 (python-dotenv 사용 시)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

# 카카오 API 키 확인
kakao_rest_key = os.getenv("KAKAO_REST_API_KEY")
kakao_key = os.getenv("KAKAO_API_KEY")

if kakao_rest_key:
    print(f"✅ KAKAO_REST_API_KEY 설정됨: {kakao_rest_key[:10]}...")
elif kakao_key:
    print(f"✅ KAKAO_API_KEY 설정됨: {kakao_key[:10]}...")
else:
    print("❌ 카카오 API 키가 설정되지 않았습니다.")
```

## 문제 해결

### 지오코딩이 작동하지 않는 경우

1. **API 키 확인**
   ```bash
   # 환경 변수가 제대로 로드되었는지 확인
   python -c "import os; print(os.getenv('KAKAO_REST_API_KEY') or os.getenv('KAKAO_API_KEY'))"
   ```

2. **API 키 형식 확인**
   - 카카오 REST API 키는 "KakaoAK " 접두사 없이 사용해야 합니다
   - geocoder는 자동으로 접두사를 제거하지만, 직접 설정 시에는 접두사 없이 설정하세요

3. **API 할당량 확인**
   - 카카오 로컬 API: 무료 할당량 300,000건/일
   - Vworld API: 무료 할당량 확인 필요

4. **로그 확인**
   ```python
   from core.logger import get_logger
   logger = get_logger(__name__)
   # 로그에서 "Kakao API key not found" 메시지 확인
   ```

## 참고

- 카카오 로컬 API 문서: https://developers.kakao.com/docs/latest/ko/local/dev-guide
- Vworld API 문서: https://www.vworld.kr/dev/v4api.do

