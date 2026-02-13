# Quickstart: Web Frontend (008)

**Branch**: `008-web-frontend`

## Prerequisites

- Node.js 20+ (LTS)
- Python 3.11+ with `uv`
- Docker & Docker Compose (for PostgreSQL, Redis, MLflow)
- Running backend stack (`docker-compose.api.yml` + `docker-compose.mlflow.yml`)

## Backend Setup (existing + new endpoints)

```bash
# Start infrastructure
docker compose -f docker/docker-compose.mlflow.yml up -d
docker compose -f docker/docker-compose.api.yml up -d --env-file .env

# Run database migrations (after adding new tables)
uv run alembic upgrade head

# Verify backend health
curl http://localhost:8000/health
```

## Frontend Setup

```bash
# Initialize Next.js project
cd frontend/
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   AUTH_SECRET=<generate with `openssl rand -base64 32`>

# Run development server
npm run dev
# → http://localhost:3000
```

## First Run

1. Open `http://localhost:3000` in browser
2. The app detects no users exist (calls `GET /auth/status`)
3. You are redirected to the setup page
4. Create the initial admin account (username + password)
5. You are automatically logged in and redirected to the chat view
6. Start chatting!

## Development Workflow

```bash
# Frontend development (with hot reload)
cd frontend/ && npm run dev

# Run frontend tests
cd frontend/ && npm test           # Vitest unit + component tests
cd frontend/ && npx playwright test # E2E tests (requires running backend)

# Run backend tests
uv run pytest tests/ -v

# Rebuild backend after code changes
docker compose -f docker/docker-compose.api.yml up -d --build
```

## Project Structure

```
D:\projects\personal-ai-assistant\
├── src/                    # Python backend (FastAPI)
│   ├── api/
│   │   ├── routes.py       # Existing + new REST endpoints
│   │   ├── auth.py         # NEW: Auth endpoints
│   │   ├── conversations.py # NEW: Conversation CRUD
│   │   ├── memories.py     # NEW: Memory browsing
│   │   ├── entities.py     # NEW: Knowledge graph browsing
│   │   └── admin.py        # NEW: User management
│   ├── models/
│   │   └── user.py         # NEW: User model
│   └── services/
│       ├── auth_service.py # NEW: JWT + password hashing
│       └── user_service.py # NEW: User CRUD
├── frontend/               # Next.js frontend (NEW)
│   ├── src/
│   │   ├── app/            # App Router pages
│   │   ├── components/     # React components
│   │   ├── lib/            # API client, SSE helper, auth config
│   │   ├── hooks/          # Custom React hooks
│   │   ├── stores/         # Zustand stores
│   │   └── types/          # TypeScript type definitions
│   └── tests/
│       ├── e2e/            # Playwright E2E tests
│       ├── components/     # Component tests (Vitest + RTL)
│       └── lib/            # Unit tests
├── docker/
│   ├── docker-compose.api.yml
│   ├── docker-compose.mlflow.yml
│   └── docker-compose.frontend.yml  # NEW
└── specs/008-web-frontend/
```

## Key URLs (Development)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MLflow | http://localhost:5001 |
