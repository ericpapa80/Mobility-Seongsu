# 모듈 경로 에러 해결 가이드

## 문제 상황

```
ModuleNotFoundError: No module named 'plugins'
```

## 원인 분석

### 1. 상대 경로 계산의 불안정성

**기존 코드**:
```python
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
```

**문제점**:
- `__file__`이 상대 경로일 경우 예상과 다른 경로를 가리킬 수 있음
- 스크립트 실행 방식에 따라 경로가 달라질 수 있음
- Windows와 Linux에서 경로 처리 방식이 다를 수 있음

### 2. 스크립트 위치에 따른 경로 깊이

```
프로젝트 루트/
└── scripts/
    └── sgis/
        └── collection/
            └── run_sgis_timeseries.py  ← 여기서 4단계 위로 올라가야 함
```

- `collection/` → `sgis/` → `scripts/` → 프로젝트 루트
- 총 3단계 위로 올라가야 함 (parent.parent.parent)

## 해결 방법

### 방법 1: `.resolve()` 사용 (권장)

```python
# 절대 경로로 변환 후 계산
script_dir = Path(__file__).resolve().parent  # scripts/sgis/collection/
project_root = script_dir.parent.parent.parent  # 프로젝트 루트
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

**장점**:
- 절대 경로로 변환하여 안정적
- 실행 위치와 무관하게 작동
- 중복 추가 방지 (`if not in sys.path`)

### 방법 2: 현재 작업 디렉토리 기준

```python
# 현재 작업 디렉토리에서 프로젝트 루트 찾기
import os
project_root = Path(os.getcwd())
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

**장점**:
- 간단함
- 프로젝트 루트에서 실행할 때만 작동

**단점**:
- 다른 디렉토리에서 실행 시 실패

### 방법 3: 환경 변수 사용

```python
import os
project_root = Path(os.environ.get('PROJECT_ROOT', Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(project_root))
```

## 적용된 해결책

`scripts/sgis/collection/run_sgis_timeseries.py`에 다음 코드를 적용했습니다:

```python
# 프로젝트 루트를 sys.path에 추가
# 스크립트 위치: scripts/sgis/collection/run_sgis_timeseries.py
# 프로젝트 루트: scripts/sgis/collection/ -> scripts/sgis/ -> scripts/ -> 프로젝트 루트
script_dir = Path(__file__).resolve().parent  # scripts/sgis/collection/
project_root = script_dir.parent.parent.parent  # 프로젝트 루트
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

## 다른 스크립트도 확인 필요

다른 스크립트들도 동일한 문제가 있을 수 있으므로 확인이 필요합니다:

- `scripts/sgis/collection/run_sgis.py`
- 기타 `scripts/` 하위의 모든 스크립트

## 테스트 방법

```bash
# 프로젝트 루트에서 실행
python scripts/sgis/collection/run_sgis_timeseries.py

# 다른 디렉토리에서 실행 (절대 경로)
python D:\VSCODE_PJT\all_scrapping\scripts\sgis\collection\run_sgis_timeseries.py
```

두 경우 모두 정상 작동해야 합니다.

## 참고

- Python의 `__file__`은 스크립트 실행 방식에 따라 상대 경로 또는 절대 경로일 수 있음
- `.resolve()`를 사용하면 항상 절대 경로를 얻을 수 있음
- `sys.path`에 중복 추가를 방지하면 성능과 안정성 향상

