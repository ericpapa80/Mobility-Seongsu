# Collectors - Framework 통합 가이드

이 문서는 `collectors/` 폴더가 Framework 프로젝트에 통합된 후의 사용 방법을 설명합니다.

## 개요

`collectors/` 폴더는 Framework 프로젝트의 독립적인 데이터 수집 시스템입니다. Python 기반으로 다양한 출처에서 데이터를 수집하고, backend API를 통해 Framework의 데이터 파이프라인과 통합됩니다.

## 구조

```
collectors/
├── core/                    # 핵심 기능 모듈
│   ├── base_scraper.py     # 기본 스크래이퍼 클래스
│   ├── runner.py           # 통합 실행기
│   ├── backend_adapter.py  # 🆕 Backend API 통합 어댑터 (Python)
│   └── backend_adapter.js  # 🆕 Backend API 통합 어댑터 (Node.js)
├── plugins/                 # 스크래이퍼 플러그인
│   ├── sgis/               # SGIS 데이터 수집
│   ├── sbiz/               # SBIZ 데이터 수집
│   └── openup/             # OpenUp 데이터 수집
├── config/                  # 설정 관리
├── data/                    # 수집된 데이터 (Git에 커밋되지 않음)
├── logs/                    # 로그 파일 (Git에 커밋되지 않음)
└── scripts/                 # 실행 스크립트
```

## Framework 통합

### 1. 환경 변수 설정

`collectors/.env` 파일을 생성하고 필요한 환경 변수를 설정하세요:

```env
# Backend API URL (Framework 통합용)
BACKEND_API_URL=http://localhost:3000

# 기존 수집기 환경 변수
SGIS_CONSUMER_KEY=your_consumer_key_here
SGIS_CONSUMER_SECRET=your_consumer_secret_here
VWORLD_API_KEY=your_vworld_api_key_here
# ... 기타 환경 변수
```

**주의**: `collectors/.env`는 프로젝트 루트의 `.env`와 별도로 관리됩니다.

### 2. Backend API 통합

수집 완료 후 자동으로 backend API로 데이터를 전송하려면:

#### Python에서 사용:

```python
from core.backend_adapter import BackendAdapter

adapter = BackendAdapter()
adapter.send_raw_data(
    collector_type='sgis',
    raw_data=collected_data,
    metadata={'source': 'sgis_api'}
)
```

#### Node.js에서 사용:

```javascript
import { getBackendAdapter } from './core/backend_adapter.js';

const adapter = getBackendAdapter();
await adapter.sendRawData('sgis', collectedData, { source: 'sgis_api' });
```

### 3. n8n 워크플로우 통합

n8n 워크플로우에서 collectors를 호출하는 방법:

#### 방법 1: Python 스크립트 직접 실행
```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.executeCommand",
      "parameters": {
        "command": "cd collectors && python -m core.runner run sgis"
      }
    }
  ]
}
```

#### 방법 2: Backend API를 통한 호출
```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:3000/api/collectors/execute/sgis",
        "method": "POST"
      }
    }
  ]
}
```

## 사용 방법

### 기본 사용 (독립 실행)

```bash
# collectors 폴더로 이동
cd collectors

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp env_template.txt .env
# .env 파일 편집

# 수집기 실행
python -m core.runner run sgis
```

### Framework 통합 사용

수집 완료 후 자동으로 backend로 전송하려면, 수집기 코드에 다음을 추가:

```python
from core.backend_adapter import get_backend_adapter

# 수집 완료 후
adapter = get_backend_adapter()
adapter.send_collection_result('sgis', collection_result)
```

## 데이터 흐름

```
collectors/ (Python 수집기)
    ↓ 수집 완료
backend_adapter.py/js
    ↓ HTTP POST
backend/api/collectors/raw
    ↓ Raw Store 저장
backend/etl/
    ↓ ETL 처리
backend/db/ (Core DB + Graph Layer)
    ↓
frontend/ (FlowShell & App Profile)
```

## 주의사항

1. **환경 변수 분리**: `collectors/.env`는 프로젝트 루트 `.env`와 별도 관리
2. **Python 의존성**: `collectors/requirements.txt`는 별도 설치 필요
3. **데이터 저장**: `collectors/data/`는 Git에 커밋되지 않음
4. **로그 파일**: `collectors/logs/`는 Git에 커밋되지 않음

## 문제 해결

### Backend API 연결 실패

1. Backend 서버가 실행 중인지 확인: `http://localhost:3000/api/health`
2. `collectors/.env`에 `BACKEND_API_URL`이 올바르게 설정되었는지 확인
3. 네트워크 방화벽 설정 확인

### Python 모듈 import 오류

1. `collectors/` 폴더에서 실행하는지 확인
2. Python 가상 환경이 활성화되었는지 확인
3. `pip install -r requirements.txt` 실행

## 관련 문서

- [원본 README](README.md): collectors 시스템 기본 사용법
- [프로젝트 구조](docs/project/STRUCTURE.md): 상세 구조 설명
- [환경 변수 가이드](docs/project/ENV_GUIDE.md): 환경 변수 설정 방법
- [Framework Backend 문서](../../backend/docs/README.md): Backend API 문서

