# 문서 인덱스

이 디렉토리는 프로젝트의 모든 문서를 체계적으로 관리합니다.

## 폴더 구조

```
docs/
├── project/          # 프로젝트 관련 문서
├── scrapers/         # 스크래이퍼 개발 가이드
├── sources/          # 출처별 스크래이핑 정보
├── metadata/         # 수집 데이터 메타데이터
└── examples/         # 예제 문서
```

## 문서 목록

### 프로젝트 문서 (`project/`)

프로젝트 전반에 관한 문서들입니다.

- **[PRD.md](project/PRD.md)**: 프로젝트 요구사항 정의서 (Product Requirements Document)
  - 프로젝트 개요 및 목적
  - 기능 요구사항 및 비기능 요구사항
  - 시스템 아키텍처
  - 기술 스택

- **[STRUCTURE.md](project/STRUCTURE.md)**: 프로젝트 구조 상세 설명
  - 폴더 구조
  - 핵심 개념
  - 확장성
  - 사용 예제

- **[MIGRATION_GUIDE.md](project/MIGRATION_GUIDE.md)**: 마이그레이션 가이드
  - 구조 개선 요약
  - 기존 코드 마이그레이션 방법
  - 호환성 정보

- **[CLEANUP_SUMMARY.md](project/CLEANUP_SUMMARY.md)**: 폴더 구조 정리 요약
  - 삭제된 레거시 파일 목록
  - 최종 폴더 구조

- **[ENV_GUIDE.md](project/ENV_GUIDE.md)**: 환경 변수 설정 가이드
  - 환경 변수 설정 방법
  - 출처별 설정 관리
  - 보안 주의사항

### 스크래이퍼 가이드 (`scrapers/`)

스크래이퍼 개발 및 사용에 관한 문서들입니다.

- **[README.md](scrapers/README.md)**: 스크래이퍼 플러그인 개발 가이드
  - 새로운 스크래이퍼 추가 방법
  - 플러그인 구조 설명
  - 베스트 프랙티스

### 출처별 정보 (`sources/`)

각 데이터 출처별 스크래이핑 정보를 관리합니다.

- **OpenUp** (`sources/openup/`): OpenUp API 관련 원본 문서
  - API 엔드포인트 정보
  - 요청/응답 예제
  - 인증 정보

- **SBIZ** (`sources/sbiz/`): 소상공인시장진흥공단 API 관련 문서
  - API 활용 가이드
  - 업종분류 정보

- **SGIS** (`sources/sgis/`): SGIS 스크래이핑 정보
  - API 엔드포인트
  - 요청 헤더 및 쿠키
  - 사용 예제

### 데이터 메타데이터 (`metadata/`)

수집된 데이터의 구조와 필드에 대한 상세 설명을 제공합니다.

- **[metadata_openup.md](metadata/openup/metadata_openup.md)**: OpenUp 데이터 메타데이터
  - 건물 데이터 구조
  - 매장 데이터 구조
  - 필드별 상세 설명
  - 데이터 타입 및 형식
  - 수집 방법 및 API 흐름

- **[metadata_foottraffic.md](metadata/foottraffic/metadata_foottraffic.md)**: Foottraffic (골목길 유동인구) 데이터 메타데이터
  - API 파라미터 및 응답 구조
  - 원본/정제 데이터 구조
  - 필드별 상세 설명
  - 중복 제거 로직
  - 성수동 좌표 범위

## 새로운 문서 추가

### 출처별 정보 추가

새로운 출처의 스크래이핑 정보를 추가할 때:

1. `docs/sources/{source_name}/` 디렉토리에 관련 파일들을 생성
2. 다음 정보 포함:
   - 출처 사이트 URL
   - API 엔드포인트 (있는 경우)
   - 요청 헤더 및 인증 정보
   - 사용 예제
   - 특이사항

### 스크래이퍼 문서 추가

새로운 스크래이퍼를 추가할 때:

1. `docs/scrapers/{scraper_name}.md` 파일 생성
2. 다음 정보 포함:
   - 스크래이퍼 개요
   - 설정 방법
   - 사용 예제
   - 문제 해결

### 데이터 메타데이터 추가

새로운 데이터 소스의 메타데이터를 추가할 때:

1. `docs/metadata/{source_name}/metadata_{source_name}.md` 파일 생성
2. 다음 정보 포함:
   - 수집 데이터 구조 설명
   - 필드별 상세 설명 (타입, 설명, 예시)
   - 데이터 수집 방법
   - API 호출 흐름
   - 출력 파일 구조

## 문서 작성 규칙

1. **명명 규칙**: 파일명은 소문자와 언더스코어 사용 (`my_document.md`)
2. **구조**: 각 문서는 목차를 포함하여 구조화
3. **링크**: 상대 경로를 사용하여 문서 간 링크 연결
4. **업데이트**: 코드 변경 시 관련 문서도 함께 업데이트

