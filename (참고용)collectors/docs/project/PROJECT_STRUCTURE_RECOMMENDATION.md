# 프로젝트 구성 추천

> 원본: [ChatGPT 대화 링크](https://chatgpt.com/share/692d3cf3-95a8-8001-8127-7ecc2750f8c6)

## 질문

스크레이핑을 SGIS와 같이 API 기반으로 수집하는 것과 네이버 리뷰, 빅카인즈와 같이 매크로로 수집하는 방식이 다른 것 같음. 모든 수집코드를 하나의 프로젝트화 하고자하는데 위 2가지 접근 방식을 하나의 프로젝트로 구성하는 것을 추천하는지

## 결론 요약

1. **SGIS 같은 API 기반 수집**과 **네이버 리뷰·BIGKINDS 같은 매크로/스크레이핑 기반 수집**은 기술 특성은 다르지만, 운영 관점에서는 동일한 "데이터 수집 파이프라인"으로 볼 수 있음.

2. 따라서 **"하나의 프로젝트(또는 모노레포)" 안에 넣되, 내부를 명확히 모듈화** 하는 방식을 추천.

3. 단, "완전한 한 파일/한 패키지"로 섞는 것이 아니라:
   - 공통 인프라(로그/설정/스케줄러/DB) = 공유
   - 수집 방식별(REST API / Selenium / 기타) = **별 모듈·플러그인** 구조로 나누는 것이 중요.

## 두 방식의 본질적 차이

### 1) API 기반 수집 (예: SGIS, 공공데이터포털)

#### 특성
- HTTP 요청(REST/JSON, XML 등) + 인증키/토큰
- 요청 파라미터와 응답 구조가 **명확히 정의** 됨 (schema 기반)
- 버전 관리와 Rate Limit 중심의 이슈

#### 실패 패턴
- 인증 실패, 쿼터 초과, 스펙 변경(버전업)
- 네트워크/타임아웃

### 2) 매크로/스크레이핑 기반 수집 (예: 네이버 리뷰, BIGKINDS)

#### 특성
- DOM 구조, JS 렌더링, 비공식 API, 로그인 세션 등 **불안정 요소** 많음
- 셀레니움/Playwright, headless 브라우저 또는 비공식 API 역추적

#### 실패 패턴
- HTML 구조 변경, CSS/JS 변경
- Bot 차단, Captcha, 로그인 세션 만료
- 속도/안정성 이슈

### 3) 공통점

#### 공통으로 필요한 것
- 스케줄링(cron, n8n, Airflow 등)
- 로깅/모니터링
- 재시도/에러 핸들링
- 결과 저장(PostgreSQL, 파일, S3 등)

즉, **상위 레벨의 "수집 파이프라인 프레임워크"는 통합** 하는 것이 합리적임.

## 하나의 프로젝트로 묶을 때의 장점

### 1) 운영·유지보수 측면

- 하나의 **config 체계**로 관리 가능
  - 예: `config/sgis.yml`, `config/naver_reviews.yml`, `config/bigkinds.yml`
- 공통 유틸 재사용
  - 요청/응답 로깅, 공통 retry 로직, proxy 설정, 알림(Slack, 이메일) 등
- 배포/버전 관리 단순화
  - Git 하나, CI/CD 하나로 전체 수집 파이프라인 관리

### 2) 데이터 파이프라인/아키텍처 측면

- **"Source 별 플러그인 구조"**로 확장 가능
  - 새로운 API, 새로운 웹사이트 추가 시 공통 인터페이스만 맞추면 됨
- Downstream(후속 분석·시각화)에서 일관된 메타데이터 사용
  - 예: `source`, `collected_at`, `batch_id`, `raw_payload` 등

### 3) 팀/조직 관점

- CommandSpace/IFE 관점에서
  - "데이터 수집 엔진"을 **단일 제품(Platform)**으로 정의 가능
  - 기술 부채를 여러 리포지토리에 분산시키지 않고 한곳에서 관리

## 주의할 점: 분리해야 할 경계

하나의 프로젝트로 묶더라도, **다음 경계는 꼭 나누는 것을 추천**.

### 1) 실행 레이어 분리

#### 예시
- `collectors/api/`: SGIS, 공공데이터, Kakao API 등
- `collectors/scraper/`: Naver, BIGKINDS, 기타 웹스크레이핑

#### 이유
- 의존성(Python 패키지, Selenium, 브라우저 드라이버 등)이 크게 다름
- 도커 이미지도 분리하는 것이 더 가벼운 경우 많음[^1]

### 2) 도메인별 스키마/정제 로직 분리

#### 예시
- `normalizers/sgis.py`: 집계구/격자/행정동 기반 인구·사업체 정제
- `normalizers/naver_reviews.py`: 리뷰 텍스트, 평점, 좌표 정제
- `normalizers/bigkinds.py`: 기사본문, 키워드, 날짜 정제

#### 이유
- 같은 "수집 엔진"이라도, **도메인 별로 정제 방식과 품질 기준이 다름**
- 향후 재사용/재분석 시 도메인별 모듈이 독립적일수록 좋음

### 3) 인프라(스케줄·큐)와 비즈니스 로직(수집 코드) 분리

#### 스케줄러/플로우 툴
- n8n / Airflow / Prefect / Temporal 등

#### 수집 로직
- 별도의 Python/Node 모듈로 구현

#### 이유
- "나중에 스케줄러를 교체해도(예: n8n → Airflow)" **수집 로직을 그대로 재사용** 할 수 있도록.

## 추천 구조 예시 (폴더/모듈 단위)

### 1) 단일 리포지토리(모노레포) 구조 예시

```
project-root/
├── configs/
│   ├── sgis.yml
│   ├── naver_reviews.yml
│   └── bigkinds.yml
├── collectors/
│   ├── __init__.py
│   ├── base_collector.py  ← 공통 인터페이스 (run(), fetch(), save() 등)
│   ├── api/
│   │   ├── sgis_collector.py
│   │   └── publicdata_collector.py
│   └── scraper/
│       ├── naver_reviews_collector.py
│       └── bigkinds_collector.py
├── normalizers/
│   ├── sgis_normalizer.py
│   ├── naver_reviews_normalizer.py
│   └── bigkinds_normalizer.py
├── storage/
│   ├── db_client.py  (PostgreSQL, Supabase, DuckDB 등)
│   └── file_store.py  (CSV/Parquet 저장)
├── orchestrator/
│   ├── cli.py  (예: python cli.py run sgis)
│   ├── scheduler_n8n.md  또는 flows/ (n8n, LangFlow 등과 연동 설명)
├── tests/
└── docs/
```

### 2) 실행 단위(도커/환경) 분리 예시

```
docker/
├── Dockerfile.api
│   └── requests, httpx 등 가벼운 API 수집용
└── Dockerfile.scraper
    └── Selenium, Playwright, 브라우저 이미지 포함 (무거운 스크레이퍼용)
```

- CI/CD: 같은 리포지토리에서 두 개의 이미지를 각각 빌드·배포

### 3) 공통 인터페이스 설계 예

#### BaseCollector
- `prepare()`: config·환경 로딩
- `fetch()`: 원시데이터 수집(API 콜, 스크레이핑 등)
- `normalize()`: 공통 스키마로 변환
- `save()`: DB/파일에 저장

SGIS / Naver / BIGKINDS 모두 이 인터페이스를 구현하게 하면 상위에서 "source 이름만 바꿔 호출" 가능.

## 향후 확장 관점에서의 제안

### 1) "수집 엔진"을 하나의 Product로 정의

- 예: `CommandSpace Data Harvester`, `Infinite Collector` 등
- 역할: 다양한 소스(SGIS, 공공데이터, 맵 리뷰, 뉴스 등)를 **플러그인 방식으로 추가** 할 수 있는 공통 엔진
- IFE/Flow 기반 UI와도 연결 가능
  - 특정 노드: "SGIS-Collector", "Naver-Review-Collector"로 배치
  - 플로우 툴(n8n)에서 **노드 하나 = 내부 Collector 하나 호출** 구조

### 2) 로깅·모니터링 일원화

- 실패/성공 로그를 한 대시보드에서 조회
  - 어느 소스가 자주 깨지는지(스크레이핑), 어느 API가 자주 타임아웃되는지
- 알림 채널 통합
  - Slack/메일/카카오 알림 등으로 공통 알림

### 3) 실험/테스트 환경 분리

- "실험용 수집 코드"도 같은 리포에 넣되 `experimental/` 폴더로 분리
  - 안정화되면 `collectors/`로 승격
- 이렇게 하면 **실험과 운영이 같은 문맥에서 관리** 되지만, 경계는 명확.

## 참고

[^1]: 예를 들어, API 전용 컨테이너는 브라우저 엔진이 필요 없기 때문에 빌드 속도/이미지 크기/배포 안정성에서 이점이 큼.

---

**출처**: [ChatGPT 대화 링크](https://chatgpt.com/share/692d3cf3-95a8-8001-8127-7ecc2750f8c6)

