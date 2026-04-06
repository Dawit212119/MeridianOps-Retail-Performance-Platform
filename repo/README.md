# MeridianOps Docker Workflow

## Start Backend + Frontend + Database

```bash
docker compose -f docker-compose.yml up --build -d
```

Or use the helper script:

```bash
./run_app.sh
```

This starts the application in detached mode and exits the terminal command while containers keep running.

Services:

- Backend API: http://localhost:8000/api/v1/health
- Frontend app: http://localhost:5173
- Postgres: localhost:5432

## Run Tests Sequentially (Backend -> Frontend)

Run this after the app stack is up:

```bash
./run_tests.sh
```

The test runner exits when done. If app services were already running before tests, they stay running.

Important: do not use `up --abort-on-container-exit` for sequential tests. That mode can stop the second test container early (exit code 137) when the first test container exits.

What this does:

- Runs backend tests first and stops on failure.
- The backend test container executes the PostgreSQL locking/concurrency suite and fails if that suite would be skipped.
- Runs frontend tests only if backend tests pass.
- Returns non-zero exit code on failure.

## Configuration

### Security & Feature Settings

| Variable | Default | Description |
|---|---|---|
| `FRONTEND_BASE_URL` | *(unset)* | Explicit base URL for share-link generation (e.g. `https://app.example.com`). **Required in production/staging** — the backend returns HTTP 400 if this is unset in non-dev environments. In `local`/`dev`/`test` envs only, the backend falls back to deriving the URL from the request's `Host` and `X-Forwarded-Proto` headers. |
| `SEED_DEMO_ENABLED` | `false` | Must be `true` to allow the `POST /api/v1/ops/seed/demo` endpoint. Even when enabled, the endpoint is blocked in `production`/`prod` environments. |
| `APP_ENV` | `local` | Environment identifier. Affects cookie secure flag and seed/demo availability. Use `production` or `prod` for live deployments. |
| `FIELD_ENCRYPTION_KEY` | *(unset)* | When set, wallet monetary columns are encrypted at rest. |

### Migration Notes (v0015–v0016)

- **0015**: `quiz_topics.code` uniqueness changed from global to `(store_id, code)`. Two stores can now have the same topic code independently.
- **0016**: `kpi_job_runs.store_ids_json` added. KPI run history is now scoped: store managers only see runs that include their store.

Run migrations after upgrading:

```bash
docker compose exec backend alembic upgrade head
```

Before production rollout, perform a dry-run of both upgrade and downgrade in staging to verify migration safety:

```bash
docker compose exec backend alembic upgrade head --sql   # review generated SQL
docker compose exec backend alembic downgrade -1 --sql   # verify rollback path
```

## Docker-Only Policy

This project must be started, tested, and validated using Docker Compose only.

Do not run backend or frontend directly on the host machine for acceptance/runtime verification.

Notes:

- Backend PostgreSQL locking tests are mandatory and always fail (never skip) when `POSTGRES_TEST_DATABASE_URL` is missing.
- The Docker test container sets `POSTGRES_TEST_DATABASE_URL` automatically, ensuring locking tests always execute in Docker and CI.

## Run Individual Test Suites In Docker

Backend only:

```bash
docker compose -f docker-compose.yml --profile test run --rm backend-tests
```

Frontend only:

```bash
docker compose -f docker-compose.yml --profile test run --rm frontend-tests
```

## Stop Everything

```bash
docker compose -f docker-compose.yml down
```

To remove the database volume too:

```bash
docker compose -f docker-compose.yml down -v
```
