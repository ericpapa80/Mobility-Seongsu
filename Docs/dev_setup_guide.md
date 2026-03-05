# 개발 환경 실행 가이드

## 사전 준비

- Python 3.11+
- Node.js 20+
- (선택) PostgreSQL + PostGIS — DB 없이도 JSON fallback 모드로 실행 가능

## 환경 변수

프로젝트 루트의 `.env_sample`을 복사하여 `.env` 파일을 생성하고, 필요한 키를 채운다.

```powershell
cp .env_sample .env
```

최소 실행에 필요한 변수:

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `VITE_API_BASE_URL` | 프론트엔드 → 백엔드 주소 | `http://localhost:8000` |
| `CORS_ORIGINS` | 백엔드 CORS 허용 도메인 | `http://localhost:5173` |
| `DATABASE_URL` | PostGIS 연결 문자열 (없으면 JSON 모드) | — |

---

## 백엔드 (FastAPI)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

서버 실행:

```powershell
uvicorn app.main:app --reload --port 8000
```

> 가상환경 없이 실행할 경우 `python -m uvicorn app.main:app --reload --port 8000`

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/api/health

> DB가 없어도 JSON fallback 모드로 정상 동작한다.

---

## 프론트엔드 (React + Vite)

```powershell
cd frontend
npm install
npm run dev
```

- 개발 서버: http://localhost:5173
- `/api/*` 요청은 Vite proxy를 통해 `localhost:8000`으로 전달된다.

### 프로덕션 빌드

```powershell
npm run build
npm run preview
```

---

## 동시 실행 (요약)

터미널 두 개를 열어 각각 실행한다.

| 터미널 | 명령 | 포트 |
|--------|------|------|
| 1 — 백엔드 | `cd backend; python -m uvicorn app.main:app --reload --port 8000` | 8000 |
| 2 — 프론트엔드 | `cd frontend; npm run dev` | 5173 |
