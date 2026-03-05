# 마이그레이션 가이드

## 구조 개선 요약

기존 구조에서 **플러그인 기반 구조**로 전환하여 20~30개 이상의 스크래이퍼 확장을 지원하도록 개선했습니다.

## 주요 변경사항

### 1. 핵심 모듈 이동

- `scrapers/base.py` → `core/base_scraper.py`
- `utils/file_handler.py` → `core/file_handler.py`
- `utils/logger.py` → `core/logger.py`

### 2. 플러그인 시스템 도입

- `scrapers/` → `plugins/` 구조로 변경
- 각 스크래이퍼가 독립적인 플러그인으로 관리
- 자동 발견 시스템 구현

### 3. 설정 분리

- `config/settings.py`에 모든 설정이 섞여있던 문제 해결
- `config/scrapers/{scraper_name}.py`로 스크래이퍼별 설정 분리

### 4. 통합 실행기

- `core/runner.py`: 모든 스크래이퍼를 통일된 방식으로 실행
- `core/scraper_registry.py`: 스크래이퍼 자동 발견 및 등록

## 기존 코드 마이그레이션

### 스크래이퍼 마이그레이션

기존 스크래이퍼를 새 구조로 마이그레이션하는 방법:

1. **폴더 이동**
   ```
   scrapers/my_scraper/ → plugins/my_scraper/
   ```

2. **Import 경로 수정**
   ```python
   # 기존
   from scrapers.base import BaseScraper
   from utils.logger import get_logger
   from utils.file_handler import FileHandler
   
   # 변경 후
   from core.base_scraper import BaseScraper
   from core.logger import get_logger
   from core.file_handler import FileHandler
   ```

3. **설정 분리**
   - `config/scrapers/my_scraper.py` 파일 생성
   - 환경 변수 관리 로직을 설정 클래스로 이동

4. **스크래이퍼 클래스 수정**
   ```python
   # plugins/my_scraper/scraper.py
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent))
   
   from core.base_scraper import BaseScraper
   # ...
   ```

### 실행 스크립트 마이그레이션

기존 개별 스크립트는 그대로 사용 가능하지만, 통합 실행기 사용을 권장합니다:

```bash
# 기존
python scripts/run_my_scraper.py

# 권장 (통합 실행기)
python -m core.runner run my_scraper
```

## 호환성

기존 코드는 다음과 같이 호환됩니다:

- `scrapers/` 디렉토리의 기존 스크래이퍼는 계속 작동 (레거시)
- `utils/` 디렉토리의 유틸리티는 계속 사용 가능 (레거시)
- 점진적으로 `plugins/`로 마이그레이션 권장

## 새로운 스크래이퍼 추가

새로운 스크래이퍼는 반드시 `plugins/` 구조를 사용하세요:

1. `plugins/new_scraper/` 폴더 생성
2. `scraper.py` 파일에 `BaseScraper` 상속 클래스 구현
3. `config/scrapers/new_scraper.py`에 설정 클래스 생성 (선택)
4. `.env` 파일에 필요한 환경 변수 추가

자세한 내용은 [스크래이퍼 플러그인 가이드](../scrapers/README.md)를 참조하세요.

## 장점

새로운 구조의 장점:

1. **확장성**: 20~30개 이상의 스크래이퍼도 체계적으로 관리 가능
2. **독립성**: 각 스크래이퍼가 완전히 독립적으로 관리됨
3. **자동화**: 스크래이퍼 자동 발견 및 등록
4. **유지보수성**: 설정과 코드가 명확히 분리됨
5. **일관성**: 모든 스크래이퍼가 동일한 인터페이스 사용

## 다음 단계

1. 기존 스크래이퍼를 `plugins/`로 마이그레이션
2. 레거시 `scrapers/` 및 `utils/` 디렉토리 정리 (선택)
3. 각 스크래이퍼에 대한 문서 작성
4. 테스트 코드 작성 (향후)

