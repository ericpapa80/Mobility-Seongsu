# Mobility Seongsu — Railway 배포 가이드

## 아키텍처 요약

- **Railway**: Frontend + Backend 단일 서비스 (Dockerfile 기반)
- **데이터**: `pipeline/silver/` JSON + `pipeline/ref/` GeoJSON → Docker 이미지에 포함
- **DB**: PostGIS (선택) — 없으면 JSON fallback 모드로 동작

---

## 배포 전 체크리스트

### 1. 버스정류장 데이터 포함 여부

버스정류장은 `pipeline/silver/bus_stops_hourly.json`에서 제공됩니다.

- [ ] `pipeline/silver/bus_stops_hourly.json` 파일 존재 확인
- [ ] 해당 파일이 Git에 커밋되어 있는지 확인

```powershell
git ls-files pipeline/silver/bus_stops_hourly.json
# 출력이 있으면 커밋됨
```

### 2. Dockerfile 데이터 복사 경로

Dockerfile에서 다음 경로가 복사됩니다:

```
COPY pipeline/silver/ ./pipeline/silver/
COPY pipeline/ref/ ./pipeline/ref/
```

`pipeline/silver/` 내 모든 JSON이 배포 이미지에 포함됩니다.

### 3. 환경 변수 (Railway 대시보드)

| 변수 | 설명 | 필수 |
|------|------|------|
| `CORS_ORIGINS` | 프론트엔드 도메인 (예: `https://xxx.railway.app`) | 권장 |
| `DATABASE_URL` | PostGIS 연결 문자열 | 선택 (없으면 JSON 모드) |
| `VITE_API_BASE_URL` | 빌드 시점에 주입 (보통 빈 값, same-origin) | 선택 |

---

## 배포 절차

### 방법 1: Git Push (권장)

Railway가 GitHub 저장소와 연결되어 있으면, `master` 브랜치에 push 시 자동 배포됩니다.

```powershell
# 1. 변경사항 스테이징
git add .

# 2. 커밋
git commit -m "feat: 업데이트 배포 (버스정류장 포함)"

# 3. 원격 저장소로 push
git push origin master
```

### 방법 2: Railway CLI

```powershell
# Railway CLI 설치 (없는 경우)
npm install -g @railway/cli

# 로그인
railway login

# 프로젝트 연결 후 배포
railway link
railway up
```

---

## 배포 후 확인

1. **헬스체크**: `https://<your-app>.railway.app/api/health`
2. **버스정류장 API**: `https://<your-app>.railway.app/api/bus-stops`
3. **프론트엔드**: `https://<your-app>.railway.app/`

버스정류장이 지도에 표시되지 않으면:
- 사이드바에서 "버스 정류장" 레이어 토글 ON
- `/api/bus-stops` 응답 확인 (빈 배열이면 JSON 파일 누락 또는 경로 오류)

---

## 로컬 프로덕션 빌드 테스트

배포 전 로컬에서 Docker 빌드로 동작 확인:

```powershell
docker build -t mobility-seongsu .
docker run -p 8000:8000 mobility-seongsu
```

이후 브라우저에서 `http://localhost:8000` 접속 후 버스정류장 레이어 확인.
