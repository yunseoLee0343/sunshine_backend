# TICKET-035 — AWS MVP Deployment Baseline

## 0. 목표

Sunshine 백엔드를 AWS EC2에 MVP 수준으로 배포한다.

이 티켓은 로컬/CI에서 검증되던 Docker Compose 기반 백엔드를 실제 AWS cloud server에서 실행 가능하게 만드는 배포 baseline이다.

이 티켓은 production-grade cloud architecture가 아니다.  
최소 목표는 아래가 AWS EC2에서 동작하는 것이다.

```text
EC2 instance
  -> Docker Engine
  -> Docker Compose
  -> backend container
  -> postgres container
  -> optional mqtt container
  -> public /healthz
  -> public /readyz
````

---

## 1. Ticket Identity

### Ticket ID

```text
TICKET-035
```

### Name

```text
AWS MVP Deployment Baseline
```

### Goal

```text
Deploy the Sunshine backend MVP to a real AWS EC2 server using Docker Compose, without introducing production-scale cloud complexity.
```

### Core output

```text
AWS EC2 deployment guide
production-safe docker compose override
server bootstrap script
environment variable template
manual deploy script
health/readiness verification script
rollback/restart instructions
security group requirements
deployment functional gate
```

### Strict non-goal

```text
no ECS
no EKS
no Kubernetes
no Terraform unless explicitly approved
no ALB
no Route53
no HTTPS automation
no autoscaling
no blue-green deployment
no canary deployment
no CloudFront
no RDS migration unless separately approved
no S3 image upload pipeline
no production observability stack
no Prometheus/Grafana
no centralized logging
no secrets manager integration unless separately approved
```

---

## 2. 배포 범위

이 티켓의 배포 방식은 **EC2 + Docker Compose**로 고정한다.

```text
Developer machine / CI
  -> SSH to EC2
  -> git pull or rsync project
  -> docker compose build
  -> docker compose up -d
  -> curl /healthz
  -> curl /readyz
```

허용 서비스:

```text
backend
postgres
mqtt
mqtt-ingest
```

필수 서비스:

```text
backend
postgres
```

조건부 서비스:

```text
mqtt:
  Ticket 6 MQTT ingestion을 배포 환경에서도 열 경우에만 사용

mqtt-ingest:
  Ticket 6 MQTT ingestion을 배포 환경에서도 실행할 경우에만 사용
```

금지 서비스:

```text
nginx
redis
vllm
llm
model-server
worker
generic-worker
grafana
prometheus
elasticsearch
kibana
```

---

## 3. 기존 티켓과의 관계

### Ticket 0과의 관계

Ticket 0의 `/healthz` liveness contract는 절대 바꾸지 않는다.

```http
GET /healthz
200
```

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

배포 환경에서도 `/healthz`는 DB, MQTT, 외부 네트워크를 체크하면 안 된다.

### Ticket 1과의 관계

Ticket 1의 `/readyz` DB readiness contract를 유지한다.

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

배포 환경에서 `/readyz`는 Postgres 연결만 확인한다.
Home Card, Rule Engine, MQTT, LLM/RAG readiness를 포함하지 않는다.

### Ticket 6과의 관계

MQTT를 AWS에서 사용할 경우:

```text
EC2 public IP:1883
  -> mqtt container
  -> mqtt-ingest
  -> backend DB path
```

센서 담당자는 MQTT broker에 아래처럼 연결한다.

```text
Host: <EC2_PUBLIC_IP>
Port: 1883
Topic: sensor/readings/{device_id}
```

Backend worker subscribe topic:

```text
sensor/readings/+
```

---

## 4. 수정/생성 허용 파일

### 수정 가능한 기존 파일

```text
docker-compose.yml
.env.example
.github/workflows/ci.yml
README.md
```

### 생성 가능한 새 파일

```text
deploy/README.md
deploy/aws/README.md
deploy/aws/ec2-bootstrap.sh
deploy/aws/deploy.sh
deploy/aws/restart.sh
deploy/aws/rollback.sh
deploy/aws/verify.sh
deploy/aws/docker-compose.prod.yml
deploy/aws/env.example
deploy/aws/security-group.md
deploy/aws/systemd/sunshine-backend.service
tests/test_ticket27_boundary.py
tests/test_deploy_config_contract.py
```

### 조건부 생성 가능

```text
.github/workflows/deploy-aws.yml
```

조건:

```text
수동 workflow_dispatch 기반이어야 한다.
GitHub Secrets를 통해서만 접속 정보를 받아야 한다.
자동 main push 배포는 금지한다.
```

---

## 5. 금지 파일/디렉터리

아래는 생성하거나 수정하지 않는다.

```text
infra/terraform/
k8s/
helm/
charts/
ecs/
eks/
cloudfront/
alb/
route53/
observability/
```

금지 이유:

```text
이 티켓은 AWS MVP deployment baseline이다.
production-scale infra-as-code나 managed orchestration은 후속 티켓으로 분리한다.
```

---

## 6. AWS 리소스 계약

이 티켓에서 사용하는 AWS 리소스는 최소화한다.

### Required

```text
EC2 instance
Security Group
Elastic IP optional
EBS volume for Docker/Postgres data optional
```

### Forbidden by default

```text
RDS
ECS
EKS
ALB
Route53
ACM
CloudFront
Secrets Manager
ECR
S3
CloudWatch custom dashboard
VPC redesign
```

### Optional but not required

```text
Elastic IP
EBS volume
```

주의:

```text
RDS를 쓰고 싶다면 별도 티켓으로 분리한다.
TICKET-0XX — AWS RDS Postgres Migration
```

---

## 7. EC2 요구사항

권장 baseline:

```text
OS: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
Instance: t3.small or t3.medium
Disk: at least 20GB
Inbound:
  TCP 22 from developer IP only
  TCP 8000 from allowed test/client IP
  TCP 1883 from sensor network only, if MQTT is enabled
Outbound:
  allow package install and GitHub access
```

금지:

```text
SSH 22 open to 0.0.0.0/0
Postgres 5432 exposed publicly
Docker daemon TCP socket exposed
AWS access keys stored on instance disk
.env with real secrets committed to Git
```

---

## 8. Security Group 계약

필수 inbound rule:

```text
SSH:
  port 22
  source: developer IP only

Backend HTTP:
  port 8000
  source: allowed client/test IP range
```

조건부 inbound rule:

```text
MQTT:
  port 1883
  source: sensor device network only
```

금지 inbound rule:

```text
Postgres:
  port 5432 public open forbidden

Docker:
  port 2375 / 2376 forbidden

All TCP:
  0.0.0.0/0 forbidden
```

---

## 9. Production Compose 계약

`deploy/aws/docker-compose.prod.yml`을 생성한다.

필수 shape:

```yaml
services:
  backend:
    build:
      context: ../..
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    ports:
      - "8000:8000"
    environment:
      APP_NAME: sunshine-backend
      APP_ENV: production
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - sunshine-postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  sunshine-postgres-data:
```

조건부 MQTT shape:

```yaml
  mqtt:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    restart: unless-stopped

  mqtt-ingest:
    build:
      context: ../..
    command: ["python", "-m", "app.mqtt.worker"]
    environment:
      APP_NAME: sunshine-backend
      APP_ENV: production
      DATABASE_URL: ${DATABASE_URL}
      MQTT_HOST: mqtt
      MQTT_PORT: "1883"
      MQTT_TOPIC: sensor/readings/+
    depends_on:
      - postgres
      - mqtt
    restart: unless-stopped
```

규칙:

```text
backend must expose 8000.
postgres must not expose 5432 publicly by default.
mqtt exposes 1883 only if Ticket 6 is enabled for deployment.
all long-lived services must use restart: unless-stopped.
```

금지:

```text
nginx service
redis service
vllm service
llm service
model-server service
generic worker service
shell command that starts multiple app processes in one container
```

---

## 10. Environment 계약

`deploy/aws/env.example`을 생성한다.

```env
APP_NAME=sunshine-backend
APP_ENV=production

POSTGRES_DB=sunshine
POSTGRES_USER=sunshine
POSTGRES_PASSWORD=replace-me-on-server-only

DATABASE_URL=postgresql+asyncpg://sunshine:replace-me-on-server-only@postgres:5432/sunshine

MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_TOPIC=sensor/readings/+
```

규칙:

```text
env.example에는 실제 secret을 넣지 않는다.
실제 .env.production은 EC2 서버에만 존재해야 한다.
.env.production은 git에 commit하지 않는다.
POSTGRES_PASSWORD는 서버에서 직접 설정한다.
DATABASE_URL password와 POSTGRES_PASSWORD는 일치해야 한다.
```

금지 env:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
VLLM_BASE_URL
LLM_BASE_URL
RAG_INDEX_URL
PGVECTOR_URL
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
JWT_SECRET
SECRET_KEY
```

---

## 11. Bootstrap Script 계약

`deploy/aws/ec2-bootstrap.sh`를 생성한다.

목적:

```text
새 EC2 Ubuntu instance에 Docker 기반 실행 환경을 준비한다.
```

필수 작업:

```text
apt update
install docker
install docker compose plugin
enable docker service
add current user to docker group
create app directory
print next manual steps
```

금지:

```text
clone private repo using embedded token
write production secrets
open firewall globally
run application automatically without env
run migrations automatically
install nginx
install Redis
install model runtimes
install GPU/NPU drivers
```

---

## 12. Deploy Script 계약

`deploy/aws/deploy.sh`를 생성한다.

필수 동작:

```text
1. verify current directory is repo root or configured app dir
2. verify .env.production exists on server
3. docker compose config validation
4. docker compose build backend
5. docker compose up -d postgres
6. wait for postgres readiness
7. run alembic upgrade head explicitly
8. docker compose up -d backend
9. optionally up mqtt/mqtt-ingest if enabled
10. run verify.sh
```

금지:

```text
run migrations during backend startup
delete postgres volume
overwrite .env.production
pull secrets from hardcoded source
auto-open AWS security group
start LLM/RAG/model services
```

---

## 13. Verify Script 계약

`deploy/aws/verify.sh`를 생성한다.

필수 checks:

```text
docker compose ps
curl http://localhost:8000/healthz
assert exact healthz JSON
curl http://localhost:8000/readyz
assert database ok
check backend container running
check postgres container running
if MQTT enabled, check mqtt and mqtt-ingest containers running
```

필수 external check 안내:

```text
from developer machine:
  curl http://<EC2_PUBLIC_IP>:8000/healthz
  curl http://<EC2_PUBLIC_IP>:8000/readyz
```

MQTT enabled일 때:

```text
sensor side must publish to:
  host: <EC2_PUBLIC_IP>
  port: 1883
  topic: sensor/readings/{device_id}
```

---

## 14. Rollback / Restart 계약

`deploy/aws/restart.sh`:

```text
docker compose restart backend
docker compose ps
./deploy/aws/verify.sh
```

`deploy/aws/rollback.sh`:

```text
git checkout <previous_commit>
docker compose build backend
docker compose up -d backend
./deploy/aws/verify.sh
```

금지:

```text
drop database
delete Docker volume
alembic downgrade automatically
```

주의:

```text
DB schema rollback은 자동화하지 않는다.
DB migration rollback은 별도 수동 절차로 둔다.
```

---

## 15. GitHub Actions 수동 배포 계약

선택적으로 `.github/workflows/deploy-aws.yml`을 생성할 수 있다.

조건:

```text
workflow_dispatch only
manual trigger only
uses GitHub Secrets
does not print secrets
does not auto-deploy on push
```

필수 secrets:

```text
AWS_EC2_HOST
AWS_EC2_USER
AWS_EC2_SSH_KEY
AWS_EC2_APP_DIR
```

금지 secrets:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
```

이 티켓에서는 AWS API를 직접 호출하지 않는다.
SSH 기반 수동 배포만 허용한다.

금지:

```text
automatic deploy on main push
docker image push to public registry
printing .env.production
creating EC2 from CI
modifying security groups from CI
```

---

## 16. Runtime 계약

허용 runtime topology:

```text
internet/client
  -> EC2_PUBLIC_IP:8000
      -> backend container
          -> GET /healthz
          -> GET /readyz
          -> product APIs

sensor device, if MQTT enabled
  -> EC2_PUBLIC_IP:1883
      -> mqtt container
      -> mqtt-ingest container
      -> postgres

backend container
  -> postgres container
```

금지 runtime topology:

```text
client -> postgres:5432
client -> Docker daemon
client -> Redis
client -> vLLM
client -> internal worker dashboard
```

---

## 17. Health / Readiness 계약

### `/healthz`

배포 후에도 Ticket 0과 동일해야 한다.

```http
GET /healthz
200
```

```json
{
  "status": "ok",
  "service": "sunshine-backend"
}
```

금지:

```text
/healthz checks Postgres
/healthz checks MQTT
/healthz checks cloud metadata
/healthz checks public IP
/healthz changes response shape
```

### `/readyz`

배포 후에도 Ticket 1과 동일하게 DB readiness만 확인한다.

```json
{
  "status": "ready",
  "service": "sunshine-backend",
  "checks": {
    "database": "ok"
  }
}
```

금지:

```text
/readyz checks AWS metadata
/readyz checks MQTT
/readyz checks Home Card data
/readyz checks Rule Engine
/readyz checks LLM/RAG
```

---

## 18. Data Persistence 계약

Postgres container data는 Docker volume에 저장한다.

필수 volume:

```text
sunshine-postgres-data
```

금지:

```text
Postgres data in container ephemeral filesystem only
SQLite fallback
JSON file persistence
local app/data DB
```

주의:

```text
EC2 instance termination can still lose data unless EBS/backup policy is configured.
Backup/restore is a later ticket.
```

후속 티켓 권장:

```text
TICKET-0XX — AWS Backup and Restore Baseline
TICKET-0XX — RDS Postgres Migration
```

---

## 19. Security 계약

필수:

```text
no secrets committed
.env.production exists only on EC2
SSH restricted to developer IP
Postgres not publicly exposed
Docker daemon not exposed
MQTT public access restricted to sensor IP range if enabled
```

금지:

```text
0.0.0.0/0 SSH
0.0.0.0/0 Postgres
hardcoded password in compose file
hardcoded private key
GitHub Actions printing env
committing .env.production
```

---

## 20. 테스트 요구사항

추가 테스트:

```text
tests/test_deploy_config_contract.py
tests/test_ticket27_boundary.py
```

### Deploy config tests

필수 확인:

```text
deploy/aws/docker-compose.prod.yml exists
deploy/aws/env.example exists
deploy/aws/deploy.sh exists
deploy/aws/verify.sh exists
deploy/aws/ec2-bootstrap.sh exists

production compose contains backend
production compose contains postgres
production compose does not expose postgres 5432 publicly by default
backend port 8000 is exposed
backend command is uvicorn app.main:app
postgres uses named volume
no nginx/redis/vllm/model-server service
```

### Boundary tests

필수 확인:

```text
no Terraform
no Kubernetes
no ECS/EKS files
no ALB/Route53/CloudFront config
no OpenAI/Anthropic/vLLM/RAG dependency
no AWS credentials committed
no .env.production committed
no migration auto-run in backend command
```

---

## 21. Functional Gate

`deploy/aws/verify.sh`는 아래를 검증해야 한다.

```bash
#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="deploy/aws/docker-compose.prod.yml"
ENV_FILE=".env.production"

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps

curl -fsS http://localhost:8000/healthz > /tmp/sunshine_deploy_healthz.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/sunshine_deploy_healthz.json").read_text())
assert body == {"status": "ok", "service": "sunshine-backend"}, body
PY

curl -fsS http://localhost:8000/readyz > /tmp/sunshine_deploy_readyz.json
python - <<'PY'
import json
from pathlib import Path
body = json.loads(Path("/tmp/sunshine_deploy_readyz.json").read_text())
assert body["status"] == "ready", body
assert body["service"] == "sunshine-backend", body
assert body["checks"]["database"] == "ok", body
assert set(body["checks"].keys()) == {"database"}, body
PY

echo "AWS MVP deployment verification: PASS"
```

EC2 외부에서 수동 확인:

```bash
curl -fsS http://<EC2_PUBLIC_IP>:8000/healthz
curl -fsS http://<EC2_PUBLIC_IP>:8000/readyz
```

MQTT enabled일 때:

```bash
mosquitto_pub \
  -h <EC2_PUBLIC_IP> \
  -p 1883 \
  -t sensor/readings/rpi-edge-node-01 \
  -m '{"reading_id":"rdg-rpi-edge-node-01-20260507T153000","device_id":"rpi-edge-node-01","plant_id":"00000000-0000-0000-0000-000000000301","measured_at":"2026-05-07T15:30:00+09:00","temperature_c":24.5,"humidity_pct":55.2,"light_lux":850.0,"soil_moisture_pct":42.0}'
```

---

## 22. Failure Classification

```text
compose_config_failure:
  docker compose config failed

missing_env_failure:
  .env.production missing on EC2

docker_build_failure:
  backend image build failed

postgres_start_failure:
  postgres container failed to start

postgres_readiness_failure:
  postgres did not become ready

migration_apply_failure:
  alembic upgrade head failed

backend_start_failure:
  backend container failed to start

healthz_contract_failure:
  /healthz unreachable or JSON drifted

readyz_contract_failure:
  /readyz unreachable or DB readiness failed

security_group_failure:
  expected public endpoint unreachable from developer machine

forbidden_service_failure:
  nginx/redis/vllm/model-server/generic worker added

secret_leak_failure:
  committed secret or .env.production detected

mqtt_deploy_failure:
  MQTT enabled but broker/ingest not running or topic contract wrong
```

---

## 23. 구현 금지 항목

이 티켓에서 구현하지 않는다.

```text
ECS
EKS
Kubernetes
Terraform
ALB
Route53
HTTPS certificate automation
CloudFront
RDS migration
Secrets Manager integration
S3 image upload
production monitoring stack
distributed tracing
autoscaling
blue-green deployment
canary deployment
Redis
vLLM
LLM/RAG service
model server
Nginx reverse proxy
admin dashboard
backup/restore automation
```

---

## 24. 최종 완료 조건

Ticket 35은 아래가 모두 만족되면 완료다.

```text
deploy/aws/README.md exists.
deploy/aws/ec2-bootstrap.sh exists.
deploy/aws/docker-compose.prod.yml exists.
deploy/aws/env.example exists.
deploy/aws/deploy.sh exists.
deploy/aws/verify.sh exists.
deploy/aws/restart.sh exists.
deploy/aws/rollback.sh exists.
security-group.md documents required inbound rules.

EC2 can run Docker Compose.
backend container runs on EC2.
postgres container runs on EC2.
backend is reachable at http://<EC2_PUBLIC_IP>:8000/healthz.
GET /healthz returns exact Ticket 0 JSON.
GET /readyz returns DB-only readiness.
alembic upgrade head is executed explicitly during deploy, not during backend startup.
postgres data uses a named Docker volume.
postgres port 5432 is not publicly exposed by default.
no secrets are committed.
no .env.production is committed.
no ECS/EKS/Kubernetes/Terraform/ALB/Route53/HTTPS/RDS/Redis/vLLM/LLM/RAG/Nginx leaks into this ticket.
if MQTT is enabled, MQTT topic remains sensor/readings/+ for backend subscription and sensor/readings/{device_id} for sensor publish.
```
