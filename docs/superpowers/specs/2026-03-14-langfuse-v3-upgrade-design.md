# LangFuse v2 to v3 Upgrade Design

## Problem

`docker-compose.langfuse.yml`에서 `langfuse/langfuse:2` 이미지를 사용 중이나, `LANGFUSE_INIT_USER_*` 등 headless initialization 환경변수 9개는 v3+ 전용 기능이다. v2에서는 이 변수들이 무시되어 초기 사용자/프로젝트 자동 생성이 동작하지 않는다.

## Scope

**범위 B (중간)**: Docker Compose 재작성 + SDK 호환성 검증 + 패키지 버전 업데이트

변경하지 않는 것:
- ADR-009 (버전이 아닌 도구 선택 결정 기록)
- 테스트 파일 (Mock 기반, 기존 테스트 통과 확인만)
- Agent 핵심 로직 (agent_node, tool_node, should_continue)

## Architecture Change: v2 vs v3

| | v2 | v3 |
|---|---|---|
| 서비스 수 | 2 (PostgreSQL + Web) | 6 (PostgreSQL + ClickHouse + Redis + MinIO + Worker + Web) |
| 트레이스 저장 | PostgreSQL | ClickHouse |
| 이벤트 큐 | 없음 | Redis |
| Blob 저장소 | 없음 | MinIO (S3 호환) |
| 백그라운드 처리 | 없음 | langfuse-worker |
| Headless Init | 미지원 | LANGFUSE_INIT_* 환경변수 |

## Changes

### 1. docker-compose.langfuse.yml (전면 재작성)

**서비스 구성:**

| 서비스 | 이미지 | 포트 | 역할 |
|--------|--------|------|------|
| langfuse-db | postgres:15 | 내부 | 메타데이터 DB (기존 유지) |
| clickhouse | clickhouse/clickhouse-server | 내부 | 트레이스/관측 데이터 |
| redis | redis:7 | 내부 | 이벤트 큐, 캐싱 |
| minio | minio/minio | 내부 | S3 호환 blob 저장소 |
| langfuse-worker | langfuse/langfuse-worker:3 | 내부 | 백그라운드 처리 |
| langfuse | langfuse/langfuse:3 | :3000 | 웹 대시보드 |

**신규 필수 환경변수:**

| 변수 | 용도 | 생성 방법 |
|------|------|----------|
| ENCRYPTION_KEY | 데이터 암호화 (64자 hex) | `openssl rand -hex 32` |
| CLICKHOUSE_URL | ClickHouse HTTP 연결 | compose 내부 |
| CLICKHOUSE_PASSWORD | ClickHouse 인증 | compose 기본값 |
| REDIS_CONNECTION_STRING | Redis 연결 | compose 내부 |

**healthcheck 체인:**
- langfuse-db: `pg_isready -U langfuse -d langfuse`
- clickhouse: HTTP health endpoint
- redis: `redis-cli ping`
- langfuse: `curl http://localhost:3000/api/public/health`
- langfuse-worker: langfuse-db + clickhouse + redis healthy 대기
- langfuse: langfuse-db + clickhouse + redis healthy 대기

**depends_on 체인:**
- langfuse-worker → langfuse-db, clickhouse, redis (service_healthy)
- langfuse → langfuse-db, clickhouse, redis (service_healthy)
- agent → langfuse (service_healthy)

**볼륨:**
- langfuse_db_data (기존 유지)
- clickhouse_data (신규)
- redis_data (신규)
- minio_data (신규)

### 2. agent/graph.py (import 경로 방어적 분기)

```python
# 기존 (v2 전용)
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

# 변경 (v3 우선 + v2 폴백)
try:
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler  # v3+
    _LANGFUSE_AVAILABLE = True
except ImportError:
    try:
        from langfuse.callback import CallbackHandler as LangfuseCallbackHandler  # v2
        _LANGFUSE_AVAILABLE = True
    except ImportError:
        _LANGFUSE_AVAILABLE = False
```

graceful degradation 패턴은 그대로 유지된다. `_get_langfuse_handler()`의 나머지 로직은 변경 없음.

### 3. pyproject.toml

```diff
- "langfuse>=2.0.0",
+ "langfuse>=3.0.0,<4",
```

### 4. agent/requirements.txt

```diff
- langfuse>=2.0.0
+ langfuse>=3.0.0,<4
```

### 5. README.md (LangFuse 섹션)

- ENCRYPTION_KEY 생성 절차 추가 (`openssl rand -hex 32`)
- .env 필수 변수 목록에 ENCRYPTION_KEY 추가
- 초기 로그인 안내 유지 (headless initialization이 v3에서 정상 동작)

## VETO Consensus

### Round 1

| 패널 | 투표 | 핵심 근거 |
|------|------|----------|
| Software Architect | VETO | SDK import 경로 v3 변경 + 검증 기준에 트레이스 기록 확인 누락 |
| DevOps Engineer | VETO | v3는 ClickHouse/Redis/Worker 필수, 단순 태그 변경으로 기동 불가 |
| Finance Domain Expert | APPROVE | Agent 핵심 기능/graceful degradation에 영향 없음 |

### Round 2 (수정안 반영)

| 패널 | 투표 | 비고 |
|------|------|------|
| Software Architect | APPROVE | 3/3 VETO 근거 해소 |
| DevOps Engineer | APPROVE | 4/4 VETO 근거 해소, 이행 조건 R-1~R-3 부여 |
| Finance Domain Expert | APPROVE | 유지 |

### DevOps 이행 조건

| # | 내용 |
|---|------|
| R-1 | ENCRYPTION_KEY는 .env에 고정값으로 생성. README에 openssl rand -hex 32 절차 명시 |
| R-2 | agent 서비스에 depends_on: langfuse: condition: service_healthy 추가 |
| R-3 | langfuse 웹 서비스에 /api/public/health healthcheck 정의 |

## Verification Criteria

1. `uv lock` 후 `uv run pytest tests/ -v` 전체 통과
2. `docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up` 시 6개 서비스 정상 기동
3. LangFuse 대시보드 :3000 로그인 가능 (headless initialization)
4. 실제 `/chat` 요청 1건 후 LangFuse Traces 탭에 트레이스 기록 확인
