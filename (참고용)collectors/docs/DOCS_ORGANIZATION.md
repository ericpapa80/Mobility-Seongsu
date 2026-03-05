# 문서 정리 요약

## 정리 완료

루트 디렉토리에 있던 모든 .md 파일을 `docs/` 폴더로 체계적으로 정리했습니다.

## 이동된 파일

### 프로젝트 문서 → `docs/project/`

- `CLEANUP_SUMMARY.md` → `docs/project/CLEANUP_SUMMARY.md`
- `STRUCTURE.md` → `docs/project/STRUCTURE.md`
- `MIGRATION_GUIDE.md` → `docs/project/MIGRATION_GUIDE.md`
- `PRD.md` → `docs/project/PRD.md`

### 출처별 정보 → `docs/sources/{source_name}/`

- `스크레이핑 사이트_정보.md` → `docs/sources/sgis/sgis.md`

## 최종 문서 구조

```
docs/
├── README.md                    # 문서 인덱스
├── DOCS_ORGANIZATION.md         # 문서 구조 정리 요약
├── project/                     # 프로젝트 관련 문서
│   ├── PRD.md                  # 프로젝트 요구사항 정의서
│   ├── STRUCTURE.md            # 프로젝트 구조 설명
│   ├── MIGRATION_GUIDE.md      # 마이그레이션 가이드
│   └── CLEANUP_SUMMARY.md      # 폴더 정리 요약
├── scrapers/                    # 스크래이퍼 개발 가이드
│   ├── README.md                # 플러그인 개발 가이드
│   └── sgis.md                  # SGIS 스크래이퍼 가이드
├── sources/                     # 출처별 스크래이핑 정보
│   ├── openup/                  # OpenUp 관련 원본 문서
│   ├── sbiz/                    # SBIZ 관련 원본 문서
│   └── sgis/                    # SGIS 관련 원본 문서
├── metadata/                    # 수집 데이터 메타데이터
│   └── openup/                  # OpenUp 데이터 메타데이터
│       ├── metadata_openup.md   # OpenUp 데이터 구조 설명
│       └── old/                 # 이전 버전 문서
└── examples/                    # 예제 문서
    └── sbiz_final_data_format.md
```

## 업데이트된 참조

- `README.md`: 모든 문서 경로를 `docs/` 하위로 업데이트
- `docs/project/MIGRATION_GUIDE.md`: 상대 경로로 수정
- `docs/project/STRUCTURE.md`: 문서 구조 설명 업데이트

## 향후 확장

### 새로운 출처 추가 시

1. `docs/sources/{source_name}/` 디렉토리 생성 및 관련 파일들 추가
2. 다음 정보 포함:
   - 출처 사이트 URL
   - API 엔드포인트
   - 요청 헤더 및 인증 정보
   - 사용 예제

### 새로운 스크래이퍼 문서 추가 시

1. `docs/scrapers/{scraper_name}.md` 파일 생성
2. 스크래이퍼별 상세 문서 작성

### 데이터 메타데이터 추가 시

1. `docs/metadata/{source_name}/metadata_{source_name}.md` 파일 생성
2. 다음 정보 포함:
   - 수집 데이터 구조 설명
   - 필드별 상세 설명
   - 데이터 타입 및 형식
   - 예제 데이터

## 루트 디렉토리

루트에는 다음 파일만 남아있습니다:

- `README.md`: 프로젝트 메인 문서 (GitHub 등에서 첫 화면으로 표시)
- 기타 설정 파일들 (`.env`, `requirements.txt` 등)

