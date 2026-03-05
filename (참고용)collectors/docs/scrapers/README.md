# 스크래이퍼 플러그인 가이드

## 새로운 플러그인 구조

이 프로젝트는 20~30개 이상의 스크래이퍼 확장을 고려하여 플러그인 방식 구조로 설계되었습니다.

## 폴더 구조

```
all_scrapping/
├── core/                    # 핵심 기능
│   ├── base_scraper.py      # 기본 스크래이퍼 클래스
│   ├── file_handler.py      # 파일 처리
│   ├── logger.py            # 로깅
│   ├── scraper_registry.py  # 스크래이퍼 레지스트리
│   └── runner.py            # 통합 실행기
├── plugins/                 # 스크래이퍼 플러그인
│   └── {scraper_name}/
│       ├── __init__.py
│       ├── scraper.py       # 스크래이퍼 구현 (필수)
│       ├── api_client.py    # API 클라이언트 (선택)
│       └── config.py        # 플러그인별 설정 (선택)
├── config/
│   ├── settings.py          # 공통 설정
│   └── scrapers/            # 스크래이퍼별 설정
│       └── {scraper_name}.py
├── data/
│   ├── raw/{scraper_name}/  # 자동 생성
│   └── processed/{scraper_name}/
└── logs/{scraper_name}/      # 스크래이퍼별 로그
```

## 새로운 스크래이퍼 추가하기

### 1. 플러그인 폴더 생성

```bash
mkdir plugins/my_scraper
```

### 2. 필수 파일 생성

#### `plugins/my_scraper/__init__.py`
```python
"""My scraper plugin."""
```

#### `plugins/my_scraper/scraper.py`
```python
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.base_scraper import BaseScraper
from core.logger import get_logger
from core.file_handler import FileHandler

logger = get_logger(__name__)


class MyScraper(BaseScraper):
    """My custom scraper."""
    
    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(name="my_scraper", output_dir=output_dir)
        self.file_handler = FileHandler()
    
    def scrape(
        self,
        save_json: bool = True,
        save_csv: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Scrape data."""
        logger.info("Starting data scraping")
        
        # Your scraping logic here
        data = {"example": "data"}
        
        # Save data
        saved_files = {}
        timestamp = self._get_timestamp()
        
        if save_json:
            json_path = self.raw_dir / timestamp / f"my_scraper_{timestamp}.json"
            saved_files['json'] = self.file_handler.save_json(data, json_path)
        
        if save_csv:
            csv_path = self.raw_dir / timestamp / f"my_scraper_{timestamp}.csv"
            saved_files['csv'] = self.file_handler.save_csv([data], csv_path)
        
        return {
            'data': data,
            'files': saved_files,
            'timestamp': timestamp
        }
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
```

### 3. 설정 파일 생성 (선택사항)

#### `config/scrapers/my_scraper.py`
```python
"""My scraper configuration."""

import os
from typing import Dict


class MyScraperConfig:
    """Configuration for My scraper."""
    
    @staticmethod
    def get_api_key() -> str:
        return os.getenv("MY_SCRAPER_API_KEY", "")
    
    @staticmethod
    def get_base_url() -> str:
        return os.getenv("MY_SCRAPER_BASE_URL", "https://api.example.com")
    
    @staticmethod
    def validate() -> bool:
        return bool(MyScraperConfig.get_api_key())
```

### 4. .env 파일에 설정 추가

```env
MY_SCRAPER_API_KEY=your_api_key_here
MY_SCRAPER_BASE_URL=https://api.example.com
```

## 스크래이퍼 실행

### 통합 실행기 사용

```bash
# 모든 스크래이퍼 목록 보기
python -m core.runner list

# 특정 스크래이퍼 실행
python -m core.runner run my_scraper

# 여러 스크래이퍼 실행
python -m core.runner run my_scraper sgis

# JSON만 저장
python -m core.runner run my_scraper --json-only

# 출력 디렉토리 지정
python -m core.runner run my_scraper --output-dir /path/to/output
```

### 개별 스크립트 사용 (선택사항)

`scripts/scrapers/run_my_scraper.py` 파일을 생성하여 개별 실행 스크립트를 만들 수 있습니다.

## 스크래이퍼 레지스트리

스크래이퍼는 자동으로 발견되고 등록됩니다:

1. `plugins/` 디렉토리를 스캔
2. 각 하위 디렉토리에서 `scraper.py` 파일 찾기
3. `BaseScraper`를 상속받는 클래스 자동 로드
4. 레지스트리에 등록

## 베스트 프랙티스

1. **명명 규칙**: 스크래이퍼 이름은 소문자와 언더스코어 사용 (`my_scraper`)
2. **에러 핸들링**: 모든 예외를 적절히 처리하고 로깅
3. **설정 검증**: `scrape()` 메서드 실행 전 설정 검증
4. **리소스 정리**: `close()` 메서드로 리소스 정리
5. **문서화**: 각 스크래이퍼에 대한 README 작성 권장

## 예제: SGIS 스크래이퍼

`plugins/sgis/` 디렉토리를 참고하여 완전한 구현 예제를 확인할 수 있습니다.

