# Sunshine Windows PowerShell One-Command Run Guide

이 문서는 Windows에서 Sunshine 레포를 한 번에 실행하기 위한 가이드입니다.

대상 레포:

```text
https://github.com/yunseoLee0343/sunshine_backend.git
```

## 생성된 스크립트

권장 위치:

```text
scripts/windows_dev_bootstrap.ps1
```

이 스크립트는 다음 작업을 자동으로 수행합니다.

1. 현재 위치 또는 상위 폴더에서 Sunshine 레포 루트를 찾음
2. 레포가 없으면 `https://github.com/yunseoLee0343/sunshine_backend.git`을 `.\sunshine_backend`로 clone
3. Docker Compose로 `postgres`, `mqtt`, `backend`, `mqtt-ingest` 실행
4. backend 컨테이너 안에서 Alembic migration 실행
5. backend 컨테이너 안에서 demo seed 실행
6. `frontend/src/api/client.ts`를 UTF-8 no BOM으로 복구/저장
7. frontend `DEMO_USER_ID`를 현재 repo seed user와 맞춤
8. `frontend/`에서 `npm install`
9. Vite dev server 실행
10. 브라우저로 `http://localhost:5173`, `http://localhost:8000/docs` 열기

## 왜 frontend UUID를 만지는가

현재 live repo의 `frontend/src/api/client.ts`는 `DEMO_USER_ID`를 export하고, Axios 기본 헤더 `X-User-Id`에 넣습니다.

```ts
const DEMO_USER_ID = '7923c9bd-80d8-d2d1-1937-b9e0e7e28887'
```

backend seed 소스인 `app/seeds/demo_seed.py`도 `DEMO_USER_ID = demo_id("user-001")` 방식으로 같은 demo user를 생성합니다. 따라서 Windows 스크립트는 frontend client 파일을 UTF-8 no BOM으로 저장하면서 이 UUID를 유지/복구합니다.

이 처리가 필요한 이유는 Windows PowerShell 5.1에서 다음 패턴을 사용하면 TypeScript 파일이 UTF-16으로 저장되어 Vite가 `stream did not contain valid UTF-8` 오류를 낼 수 있기 때문입니다.

```powershell
Get-Content .\src\api\client.ts | Set-Content .\src\api\client.ts
```

## 사전 준비

Windows에 아래 도구가 필요합니다.

```text
Docker Desktop
Node.js LTS
npm
Git for Windows
PowerShell 5.1 이상
```

Docker Desktop은 실행 중이어야 합니다.

## 가장 단순한 실행법

레포 루트에서:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows_dev_bootstrap.ps1
```

또는 PowerShell 안에서:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows_dev_bootstrap.ps1
```

성공하면 다음 주소가 열립니다.

```text
Frontend:     http://localhost:5173
Backend docs: http://localhost:8000/docs
```

## 레포를 아직 clone하지 않은 경우

스크립트를 아무 폴더에 두고 실행해도 됩니다. 현재 폴더 아래에 `sunshine_backend`가 없으면 자동으로 clone합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\windows_dev_bootstrap.ps1
```

특정 위치를 지정하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows_dev_bootstrap.ps1 -RepoRoot D:\sunshine_backend
```

## 깨끗한 DB로 다시 시작

기존 PostgreSQL Docker volume까지 삭제하고 새 seed를 넣으려면:

```powershell
.\scripts\windows_dev_bootstrap.ps1 -ResetPostgres
```

주의: `-ResetPostgres`는 Docker Compose volume을 삭제합니다. 로컬 DB 데이터가 사라집니다.

## 최신 코드 pull 후 실행

```powershell
.\scripts\windows_dev_bootstrap.ps1 -PullLatest
```

## npm install 생략

이미 `node_modules`가 있고 package 변경이 없으면:

```powershell
.\scripts\windows_dev_bootstrap.ps1 -SkipNpmInstall
```

## 브라우저 자동 열기 끄기

```powershell
.\scripts\windows_dev_bootstrap.ps1 -NoBrowser
```

## frontend를 현재 창에서 실행

기본값은 새 PowerShell 창에서 `npm run dev`를 실행합니다. 현재 창에서 실행하려면:

```powershell
.\scripts\windows_dev_bootstrap.ps1 -ForegroundFrontend
```

## 상태 확인 명령어

레포 루트에서:

```powershell
docker compose ps
```

backend 로그:

```powershell
docker compose logs -f backend
```

전체 stack 종료:

```powershell
docker compose down
```

DB volume까지 삭제:

```powershell
docker compose down -v
```

backend health check:

```powershell
Invoke-RestMethod http://localhost:8000/healthz
```

backend ready check:

```powershell
Invoke-RestMethod http://localhost:8000/readyz
```

home API smoke test:

```powershell
$headers = @{
  "X-User-Id" = "7923c9bd-80d8-d2d1-1937-b9e0e7e28887"
}

Invoke-RestMethod http://localhost:8000/home -Headers $headers
```

## 문제 해결

### `Docker is installed but not running`

Docker Desktop을 실행한 뒤 다시 실행합니다.

```powershell
.\scripts\windows_dev_bootstrap.ps1
```

### `port is already allocated`

8000, 5173, 5432, 1883 중 하나를 다른 프로세스가 사용 중입니다.

확인:

```powershell
netstat -ano | findstr ":8000"
netstat -ano | findstr ":5173"
netstat -ano | findstr ":5432"
netstat -ano | findstr ":1883"
```

Docker Compose stack 종료:

```powershell
docker compose down
```

### Vite 오류: `stream did not contain valid UTF-8`

스크립트를 다시 실행합니다. 스크립트가 `frontend/src/api/client.ts`를 UTF-8 no BOM으로 다시 저장합니다.

```powershell
.\scripts\windows_dev_bootstrap.ps1 -SkipNpmInstall
```

### frontend는 뜨는데 API가 403 또는 빈 화면

frontend의 `DEMO_USER_ID`와 backend seed user가 안 맞는 상태일 가능성이 있습니다. 스크립트를 다시 실행하면 `client.ts`의 UUID를 repo seed user로 맞춥니다.

```powershell
.\scripts\windows_dev_bootstrap.ps1 -SkipNpmInstall
```

### migration 또는 seed 실패

backend 로그를 먼저 확인합니다.

```powershell
docker compose logs -f backend
```

깨끗한 DB가 필요하면:

```powershell
.\scripts\windows_dev_bootstrap.ps1 -ResetPostgres
```

## 스크립트가 만드는 실행 구성

```text
Docker Compose
  ├─ postgres      localhost:5432
  ├─ mqtt          localhost:1883
  ├─ backend       localhost:8000
  └─ mqtt-ingest

Local frontend
  └─ Vite          localhost:5173
       /api/v1/* → http://localhost:8000/*
```

frontend proxy는 `frontend/vite.config.ts`에 정의되어 있습니다. `/api/v1` prefix를 제거해서 backend root route로 전달합니다.

## 권장 커밋 경로

레포에 추가할 때는 아래 위치를 권장합니다.

```text
scripts/windows_dev_bootstrap.ps1
docs/WINDOWS_PS1_RUN_GUIDE.md
```
