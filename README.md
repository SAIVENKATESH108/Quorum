# Quorum

> Multi-agent AI research and report-generation platform.

## Prerequisites

Ensure you have the following installed on your system:

- **Node.js**: `v20.x` or later (tested on Node `v24+`) and `npm`
- **Python**: `3.11` or later (with [`uv`](https://github.com/astral-sh/uv) recommended)
- **Docker & Docker Compose**: For containerized local development and databases
- **Git**

---

## Getting Started

### 1. Environment Configuration

Copy the example environment file and fill in the required API keys and credentials:

```bash
cp .env.example .env
```

---

## Running with Docker Compose

Spin up the entire stack (PostgreSQL with `pgvector`, Redis, FastAPI backend, and Next.js frontend):

```bash
# Start all services
docker compose up --build

# Or run in detached mode
docker compose up -d

# To spin up only database and cache:
docker compose up -d postgres redis
```

Services will be accessible at:
- **Web Frontend**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend**: [http://localhost:8000](http://localhost:8000)
- **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **PostgreSQL (pgvector)**: `localhost:5432`
- **Redis**: `localhost:6379`

---

## Running Independently for Local Development

### Backend (`apps/api`)

1. Navigate to the API directory:
   ```bash
   cd apps/api
   ```
2. Sync dependencies using `uv`:
   ```bash
   uv sync
   ```
3. Start the FastAPI development server:
   ```bash
   uv run uvicorn src.main:app --reload --port 8000
   ```
4. Verify backend health:
   ```bash
   curl http://localhost:8000/health
   # Returns: {"status":"ok"}
   ```

### Frontend (`apps/web`)

1. Navigate to the Web directory:
   ```bash
   cd apps/web
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Shared Types (`packages/shared-types`)

To build or check types across the monorepo:
```bash
cd packages/shared-types
npm run typecheck
```

---

## Monorepo Structure

```text
quorum/
├── apps/
│   ├── web/               # Next.js 14 frontend (App Router, TypeScript, Tailwind CSS)
│   └── api/               # FastAPI backend (Python 3.11+, uv, subpackages for agents & workers)
├── packages/
│   └── shared-types/      # TypeScript types shared between web and Node tooling
├── infra/
│   ├── docker-compose.yml # Compose config for infrastructure services
│   └── migrations/        # Database migrations placeholder
├── docker-compose.yml     # Root-level docker compose orchestration
├── .env.example           # Canonical environment variable template
├── .gitignore             # Root gitignore
└── README.md              # Project documentation
```

---

## Architecture

*(Placeholder — to be filled in with multi-agent orchestration flows, vector retrieval pipelines, and report generation lifecycles).*
