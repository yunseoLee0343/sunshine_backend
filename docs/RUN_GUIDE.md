# Sunshine — 로컬 실행 가이드

> **목표** — 이 문서 하나로 백엔드 · 인프라 · 프론트엔드를 모두 구동하고
> 브라우저에서 첫 화면을 확인하는 것. **예상 소요 시간: 10분.**
>
> **현재 상태** — 외부 AI API 없이 100% 로컬 실행 가능.
> LLM · 비전 · 음성 · 식물 종 판별은 모두 결정론적 Mock으로 동작함.
> 자세한 내용은 [`docs/MOCK_TECHNICAL_DEBT.md`](./MOCK_TECHNICAL_DEBT.md) 참고.

---

## 목차

1. [필수 도구 확인](#1-필수-도구-확인)
2. [인프라 구동 (Docker)](#2-인프라-구동-docker)
3. [백엔드 설정 및 실행](#3-백엔드-설정-및-실행)
4. [DB 마이그레이션 및 시드 데이터](#4-db-마이그레이션-및-시드-데이터)
5. [프론트엔드 설정 및 실행](#5-프론트엔드-설정-및-실행)
6. [정상 동작 확인](#6-정상-동작-확인)
7. [Golden Path 시연](#7-golden-path-시연)
8. [문제 해결](#8-문제-해결)

---

## 1. 필수 도구 확인

아래 명령어를 터미널에서 실행해 버전이 출력되는지 확인하세요.

```bash
docker --version        # Docker Desktop 4.x 이상
docker compose version  # v2.x 이상 (docker-compose 아님)
python --version        # 3.11 이상
node --version          # 18.x 이상
npm --version           # 9.x 이상
```

> **Windows 사용자** — PowerShell 또는 Git Bash를 사용하세요.
> WSL2 기반 Docker Desktop을 권장합니다.

---

## 2. 인프라 구동 (Docker)

PostgreSQL 16 과 Eclipse Mosquitto 2 (MQTT 브로커) 를 Docker로 실행합니다.

```bash
# 프로젝트 루트에서 실행
docker compose up -d postgres mqtt
```

컨테이너 상태 확인:

```bash
docker compose ps
```

예상 출력:

```
NAME                      STATUS
sunshine_backend-postgres-1   Up (healthy)
sunshine_backend-mqtt-1       Up (healthy)
```

두 서비스가 모두 `healthy` 상태가 될 때까지 10–20초 기다립니다.

> **포트 정보**
> | 서비스 | 호스트 포트 | 컨테이너 포트 |
> |--------|------------|--------------|
> | PostgreSQL | 5432 | 5432 |
> | MQTT | 1883 | 1883 |

---

## 3. 백엔드 설정 및 실행

### 3-1. 가상 환경 생성 및 패키지 설치

```bash
# 프로젝트 루트에서 실행
python -m venv .venv

# 활성화
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# 개발 의존성 포함 설치 (pyproject.toml 기반)
pip install -e ".[dev]"
```

### 3-2. 환경 변수 설정

```bash
# .env.example → .env 복사
cp .env.example .env
```

`.env` 파일은 기본값 그대로 사용해도 됩니다. 로컬 개발용으로 이미 설정되어 있습니다.

```dotenv
DATABASE_URL=postgresql+asyncpg://sunshine:change-me-local-only@localhost:5432/sunshine
APP_ENV=local
```

### 3-3. 백엔드 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

아래와 같은 로그가 출력되면 정상입니다:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## 4. DB 마이그레이션 및 시드 데이터

> **백엔드가 실행 중인 상태에서 새 터미널을 열고** 가상 환경을 다시 활성화한 뒤 진행합니다.

### 4-1. 마이그레이션 실행

```bash
alembic upgrade head
```

마이그레이션 로그가 순서대로 출력됩니다:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_..., create users
INFO  [alembic.runtime.migration] Running upgrade  -> 0002_..., create plants
...
INFO  [alembic.runtime.migration] Running upgrade  -> 0009_ticket34_evaluations
```

### 4-2. 데모 시드 데이터 주입

```bash
python -m app.seeds.demo_seed
```

성공 시 아래 형태의 JSON이 출력됩니다:

```json
{
  "demo_user_id": "7923c9bd-80d8-d2d1-1937-b9e0e7e28887",
  "plant_id": "23d1867e-f2d0-5bf7-a4c3-f3568c06aeea",
  "species_count": 5,
  "knowledge_chunks": 12,
  ...
}
```

> 이 명령은 **멱등(idempotent)** 합니다. 반복 실행해도 중복 데이터가 생기지 않습니다.

**생성되는 데모 데이터:**

| 항목 | 값 |
|------|-----|
| 데모 유저 UUID | `7923c9bd-80d8-d2d1-1937-b9e0e7e28887` |
| 식물 (초록이, 몬스테라) | `23d1867e-f2d0-5bf7-a4c3-f3568c06aeea` |
| 등록 식물 종 | 몬스테라 · 포토스 · 필로덴드론 · 스파티필룸 · 산세베리아 |
| 토양수분 상태 | 18% (임계값 20% 미만 → 물주기 경보 발생) |

---

## 5. 프론트엔드 설정 및 실행

```bash
cd frontend
npm install
npm run dev
```

아래 출력이 나오면 준비 완료입니다:

```
  VITE v8.x.x  ready in 300ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

브라우저에서 `http://localhost:5173` 을 열면 Sunshine 앱이 표시됩니다.

> **프록시 설정** — Vite dev 서버는 `/api/v1/*` 경로를 자동으로
> `http://localhost:8000` (백엔드) 으로 프록시합니다. CORS 설정 불필요.

---

## 6. 정상 동작 확인

### 6-1. API 헬스 체크

```bash
# Liveness (DB 미확인)
curl http://localhost:8000/healthz
# 예상 응답: {"status":"ok","service":"sunshine-backend"}

# Readiness (DB 연결 확인)
curl http://localhost:8000/readyz
# 예상 응답: {"status":"ready","checks":{"database":"ok"}}
```

### 6-2. 데모 유저 홈 화면 API 확인

> ⚠️ **모든 API 요청에는 `X-User-Id` 헤더가 필수입니다.**

```bash
curl http://localhost:8000/home \
  -H "X-User-Id: 7923c9bd-80d8-d2d1-1937-b9e0e7e28887"
```

`plants` 배열에 초록이(몬스테라)가 포함된 JSON이 응답되면 정상입니다.

### 6-3. MQTT 센서 데이터 테스트

`mosquitto_pub` 가 설치되어 있거나 Docker 컨테이너를 통해 테스트합니다.

```bash
# 호스트에 mosquitto-clients 설치된 경우
mosquitto_pub -h localhost -p 1883 \
  -t "sensors/device-monstera-001/readings" \
  -m '{
    "reading_id": "test-001",
    "plant_id": "23d1867e-f2d0-5bf7-a4c3-f3568c06aeea",
    "device_id": "device-monstera-001",
    "sensor_type": "soil_moisture_pct",
    "value": 15.0,
    "unit": "pct",
    "measured_at": "2026-05-11T12:00:00Z"
  }'
```

```bash
# Docker 컨테이너를 통한 테스트 (mosquitto-clients 미설치 시)
docker compose exec mqtt \
  mosquitto_pub -h localhost -p 1883 \
  -t "sensors/device-monstera-001/readings" \
  -m '{"reading_id":"test-002","plant_id":"23d1867e-f2d0-5bf7-a4c3-f3568c06aeea","device_id":"device-monstera-001","sensor_type":"soil_moisture_pct","value":15.0,"unit":"pct","measured_at":"2026-05-11T12:00:00Z"}'
```

백엔드 로그에 `sensor reading ingested` 메시지가 출력되면 정상입니다.

### 6-4. OpenAPI 문서

백엔드 실행 중 `http://localhost:8000/docs` 에서 Swagger UI를 통해 모든 API를 탐색할 수 있습니다.

---

## 7. Golden Path 시연

브라우저에서 아래 순서로 진행하세요.

```
① http://localhost:5173 접속
   → 홈 화면에서 "초록이(몬스테라)" 카드 확인

② 식물 카드 클릭
   → Plant Detail 페이지: 환경 지표 · 캐릭터 상태 확인
   → 토양수분 18% (임계값 미달) → "물주기 필요" 캐릭터 표시

③ 하단 탭 "케어 로그" 클릭
   → "물줬어요" 버튼 탭 → 캐릭터 상태 변화 확인

④ 하단 탭 "채팅" 클릭
   → "물은 얼마나 자주 줘야 해?" 입력 후 전송
   → 4-섹션 답변(결론 · 근거 · 행동 · 주의) 표시 확인
   → "동반 식물 추천해줘" 입력
   → 채팅 답변 하단에 동반 식물 인라인 카드 표시 확인

⑤ 하단 탭 "히스토리" 클릭
   → 케어 로그 · 환경 요약 · 캐릭터 변화 타임라인 확인
```

> **Mock 동작 안내** — 채팅 답변은 프롬프트 해시 기반 고정 텍스트입니다.
> 동일 질문은 항상 동일한 답변을 반환하며, 이는 의도된 Mock 동작입니다.
> 실제 AI 연동 계획은 `docs/MOCK_TECHNICAL_DEBT.md` 참고.

---

## 8. 문제 해결

### DB 연결 오류

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**원인 / 해결:**
1. PostgreSQL 컨테이너 상태 확인: `docker compose ps postgres`
2. `healthy` 가 아니면 재시작: `docker compose restart postgres`
3. 포트 충돌 확인: `lsof -i :5432` (macOS/Linux) 또는 `netstat -ano | findstr 5432` (Windows)
   - 로컬 PostgreSQL 이 실행 중이면 중지하거나 `docker-compose.yml` 의 호스트 포트를 `5433:5432` 로 변경 후 `.env` 도 동일하게 수정.

---

### 마이그레이션 실패

```
FAILED: Can't locate revision identified by '...'
```

**해결:**
```bash
# 현재 리비전 확인
alembic current

# DB를 완전히 초기화하고 재마이그레이션 (데이터 삭제됨)
docker compose down -v          # 볼륨까지 삭제
docker compose up -d postgres mqtt
alembic upgrade head
python -m app.seeds.demo_seed
```

---

### 포트 충돌

| 포트 | 충돌 서비스 | 해결 방법 |
|------|------------|---------|
| 5432 | 로컬 PostgreSQL | `brew services stop postgresql` 또는 `docker-compose.yml` 에서 호스트 포트 변경 |
| 1883 | 로컬 Mosquitto | `brew services stop mosquitto` 또는 호스트 포트 `1884:1883` 으로 변경 |
| 8000 | 다른 uvicorn 프로세스 | `kill $(lsof -t -i:8000)` |
| 5173 | 다른 Vite 인스턴스 | `npm run dev -- --port 5174` |

---

### 프론트엔드 API 요청 실패 (Network Error)

**원인 / 해결:**
1. 백엔드가 실행 중인지 확인: `curl http://localhost:8000/healthz`
2. `frontend/vite.config.ts` 프록시 대상이 `http://localhost:8000` 인지 확인.
3. 브라우저 콘솔에서 401 오류 → `X-User-Id` 헤더가 Axios 클라이언트(`src/api/client.ts`)에 설정되어 있는지 확인.

---

### Mock 로직 관련 FAQ

| 증상 | 원인 | 정상 여부 |
|------|------|---------|
| 채팅 답변이 항상 비슷한 텍스트 | LLM Mock (T-018) | ✅ 정상 |
| 식물 사진 업로드 후 종 판별 미동작 | Vision Mock + 이미지 URI Mock (T-030) | ✅ 정상 |
| 음성 입력 버튼 없음 | 음성 UI 미구현 (T-031) | ✅ 정상 |
| 외부 API 키 불필요 | 전체 AI 스택 Mock | ✅ 정상 |

> 외부 서비스 연동은 `docs/MOCK_TECHNICAL_DEBT.md` 의 **교체 우선순위** 순서로 진행 예정.

---

## 전체 서비스 종료

```bash
# 인프라 컨테이너 중지 (데이터 보존)
docker compose stop postgres mqtt

# 인프라 + 볼륨 완전 삭제 (초기화)
docker compose down -v
```

백엔드(`uvicorn`)와 프론트엔드(`vite`)는 각 터미널에서 `Ctrl+C` 로 종료합니다.
