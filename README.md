# Quorum

> **Multi-agent AI research and report-generation platform.**  
> Transform complex research queries into rigorously cited, fact-checked intelligence reports in minutes using parallel agent swarms.

[![Live Web App](https://img.shields.io/badge/Live%20App-Vercel-black?logo=vercel)](https://quorum-research.vercel.app)
[![API Status](https://img.shields.io/badge/API-Live%20(200%20OK)-success?logo=fastapi)](https://api.quorum-research.up.railway.app/health)
[![Interactive Docs](https://img.shields.io/badge/Swagger-OpenAPI-brightgreen?logo=swagger)](https://api.quorum-research.up.railway.app/docs)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌐 Live Production Deployments

| Component | Provider | Live URL / Endpoint |
|---|---|---|
| **Web Dashboard** | **Vercel** | [https://quorum-research.vercel.app](https://quorum-research.vercel.app) |
| **Backend REST API** | **Railway / Fly.io** | [https://api.quorum-research.up.railway.app](https://api.quorum-research.up.railway.app) |
| **Health Probe** | **Railway / Fly.io** | [https://api.quorum-research.up.railway.app/health](https://api.quorum-research.up.railway.app/health) |
| **API Documentation** | **FastAPI Swagger** | [https://api.quorum-research.up.railway.app/docs](https://api.quorum-research.up.railway.app/docs) |
| **Real-Time WebSocket** | **WSS Endpoint** | `wss://api.quorum-research.up.railway.app/ws/reports/{report_id}` |

---

## 🎯 The Problem It Solves

Modern foundation models fail at rigorous, long-form research:
1. **Single-Turn Blindness**: Monolithic LLM prompts lack the context window and architectural structure to independently explore orthogonal sub-problems in parallel.
2. **Unchecked Hallucinations**: Standard AI assistants generate authoritative-sounding claims accompanied by fabricated DOIs, broken URLs, and invalid academic citations.
3. **Opaque Synthesis**: Users have no visibility into how conclusions were derived, which claims were verified, or where conflicting evidence was reconciled.
4. **Analyst Burnout**: Investment analysts, strategy consultants, and technical researchers spend 15–20 hours per topic manually searching databases, aggregating literature, validating sources, and drafting structured documents.

**Quorum** eliminates this bottleneck. By treating comprehensive research not as a chat completion, but as an **asynchronous distributed multi-agent DAG (Directed Acyclic Graph)**, Quorum orchestrates parallel researchers, adversarial fact-checkers, and synthesis writers to produce institutional-grade intelligence reports backed by verifiable citations.

---

## 🏛️ Architecture & System Topology

```mermaid
flowchart TD
    subgraph Client Layer ["Client Layer (Edge & Browser)"]
        Browser["User Browser / Judge UI"]
    end

    subgraph Edge Layer ["Frontend Edge Hosting (Vercel)"]
        NextWeb["Next.js 14 App Router<br/>(React Server Components + Zustand + TanStack Query)"]
        ClerkEdge["Clerk Edge Middleware<br/>(Route Protection & Token Passing)"]
    end

    subgraph Auth Provider ["Identity & Auth (Clerk)"]
        ClerkAuth["Clerk Identity Platform<br/>(JWKS / Asymmetric RS256 Tokens)"]
    end

    subgraph Backend Layer ["Backend Cluster (Railway / Fly.io)"]
        ReverseProxy["Reverse Proxy / SSL Termination<br/>(Proxy Headers & Sticky WS)"]
        FastAPI["FastAPI ASGI Server (Uvicorn)<br/>(/api/projects, /api/reports, /health)"]
        Worker["Async Arq Worker Service<br/>(Multi-Agent DAG Execution Swarm)"]
    end

    subgraph State & Bus Layer ["Managed Cloud Infrastructure (Neon & Redis)"]
        Postgres[("Managed PostgreSQL 16 (Neon)<br/>(pgvector Extension + Relational Schema)")]
        RedisPubSub[("Managed Redis 7<br/>(Arq Queue Broker & Redis Pub/Sub Event Bus)")]
    end

    Browser -->|"HTTPS (REST)"| NextWeb
    Browser -->|"WSS WebSocket (?token=)"| ReverseProxy
    Browser -->|"Auth Sign In / Sign Up"| ClerkAuth
    NextWeb --> ClerkEdge
    ClerkEdge -->|"Forward with Bearer Token"| ReverseProxy
    ReverseProxy -->|"Proxy Headers"| FastAPI
    ReverseProxy -->|"WebSocket Upgrade"| FastAPI
    FastAPI -->|"Verify JWKS / Upsert User"| Postgres
    FastAPI -->|"Enqueue AgentTaskCommand"| RedisPubSub
    Worker -->|"Pop Tasks & Run Agent Swarm"| RedisPubSub
    Worker -->|"Dual-Write State & Sections"| Postgres
    Worker -->|"Publish StatusEvent (report:{id}:events)"| RedisPubSub
    RedisPubSub -->|"Broadcast Live Telemetry"| FastAPI
    FastAPI -->|"Forward Live JSON Frame"| Browser
```

---

## 🧠 How the AI Layer Works

Quorum's intelligence pipeline is modeled as an asynchronous Directed Acyclic Graph governed by the **Strategy**, **Factory**, and **Command** design patterns:

### 1. Topological Multi-Agent DAG
```text
                  [User Query]
                       │
             ┌─────────▼─────────┐
             │ OrchestratorAgent │  (Decomposes query into 3-6 orthogonal subtopics)
             └─────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐   (Wavefront: asyncio.gather parallel execution)
         ▼             ▼             ▼
   [Researcher 1] [Researcher 2] [Researcher 3]
         │             │             │
         └─────────────┼─────────────┘
                       │
             ┌─────────▼─────────┐
             │  FactCheckerAgent │  (Adversarial cross-examination & confidence scoring)
             └─────────┬─────────┘
                       │
             ┌─────────▼─────────┐
             │    WriterAgent    │  (Structured report synthesis & inline [n] citations)
             └─────────┬─────────┘
                       ▼
            [Institutional Report]
```

1. **OrchestratorAgent**: Decomposes queries into mutually exclusive, collectively exhaustive subtopics and compiles a topological task DAG.
2. **ResearcherAgent Swarm**: Multiple independent researchers execute concurrently via `asyncio.gather`. Each worker explores primary literature, extracts key claims, and binds sources.
3. **FactCheckerAgent**: Acts as a synchronization barrier. Ingests all candidate claims, verifies evidence against source URLs, flags contradictions, and calculates a statistical confidence score (0.0 to 1.0).
4. **WriterAgent**: Consumes verified claims and generates cohesive, sectioned reports with interactive inline citations linked to the bibliography.

### 2. Multi-Provider Fault Tolerance & Strategy Pattern
External LLM APIs are abstracted behind the `AIProvider` strategy interface:
* **Supported Providers**:
  * **Anthropic Claude**: Complex reasoning and multi-perspective synthesis.
  * **OpenAI GPT**: Fast parallel research subtopic extraction.
  * **Evorozen Neural Pulse**: Specialized neural intelligence provider.
* **Circuit Breaker Pattern**:
  * Tracks consecutive provider failures (threshold: 3).
  * Automatically trips to `OPEN` state for 60 seconds to prevent resource exhaustion and cascading failures.
  * Enters `HALF_OPEN` state after cooldown, attempting a single canary request to safely restore operations.
* **Exponential Backoff with Jitter**: Automatically retries transient 429s or 5xx server errors with jittered backoff ($0.5s \times 2^{\text{attempt}}$).
* **Provider Fallback Chain**: If a provider remains unavailable or trips its circuit breaker, requests fail over instantly to the next configured provider in the fallback chain.

---

## 💻 Full Tech Stack & Architectural Justification

| Layer | Technology | Architectural Justification |
|---|---|---|
| **Frontend Framework** | **Next.js 14 (App Router)** | Leverages React Server Components for fast initial page loads, dynamic edge rendering, and built-in API routing. |
| **Styling & Theming** | **Tailwind CSS + CSS Variables** | Custom design system with tokens (`bg`, `surface`, `border`, `accent`) providing accessible light/dark theme switching without layout reflows. |
| **UI Primitives** | **shadcn/ui + Framer Motion** | Accessible, headless primitives with hardware-accelerated animations for live DAG execution telemetry and status cards. |
| **Client State & Cache** | **Zustand + TanStack Query** | Strict separation of concerns: Zustand manages ephemeral UI drawer/modal state; TanStack Query manages asynchronous server state and caching. |
| **Backend Framework** | **FastAPI (Python 3.11+)** | High-throughput asynchronous ASGI web framework with native type enforcement via Pydantic v2 and OpenAPI documentation. |
| **Database & Vectors** | **PostgreSQL 16 + `pgvector` (Neon)** | ACID compliance for relations (`users`, `projects`, `reports`) paired with vector extensions for semantic source similarity search. |
| **Task Queue & Pub/Sub** | **Redis 7 + Arq** | Pure async-native Python queue (`arq`) utilizing Redis streams for task dispatch and pub/sub channels for sub-50ms WebSocket broadcasting. |
| **Authentication** | **Clerk** | Turnkey authentication featuring edge middleware route protection and asymmetric RS256 JWKS verification on the backend. |

---

## 🛠️ Step-by-Step Local Setup

### Prerequisites
* **Node.js**: `v20.x` or later (tested on Node `v24+`) and `npm`
* **Python**: `3.11+` (with `uv` recommended)
* **Docker & Docker Compose**: For local PostgreSQL and Redis
* **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/quorum.git
cd quorum
```

### 2. Configure Environment Variables
Copy the template `.env.example` to create root and app-specific configuration:
```bash
cp .env.example .env
```
Fill in your provider API keys and Clerk credentials:
```ini
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/quorum
REDIS_URL=redis://localhost:6379/0

ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
NEURAL_PULSE_API_KEY=your_neural_pulse_api_key

CLERK_SECRET_KEY=your_clerk_secret_key
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 3. Spin Up Infrastructure via Docker Compose
Start local PostgreSQL with `pgvector` and Redis:
```bash
docker compose up -d postgres redis
```
*(Or spin up the full multi-container stack with `docker compose up --build`)*.

### 4. Run Database Migrations
Navigate to `apps/api` and apply Alembic migrations:
```bash
cd apps/api
# If using uv (recommended):
uv sync
uv run alembic upgrade head

# Or standard pip virtual environment:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
alembic upgrade head
```

### 5. Start the Backend API Server
```bash
# In apps/api directory:
uv run uvicorn src.main:app --reload --port 8000
```
Verify the server is running:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 6. Start the Asynchronous Task Worker
In a separate terminal, launch the Arq worker process:
```bash
cd apps/api
uv run python -m src.workers.main
```

### 7. Start the Frontend Development Server
In another terminal, launch the Next.js frontend:
```bash
cd apps/web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Running Automated Tests

Run the full end-to-end test suite (authentication, rate limiting, DAG orchestration, circuit breaker):
```bash
cd apps/api
uv run pytest tests/ -v
```

---

## 🚀 Advanced Extensions (Lane F)

Quorum features modular extensions designed for enterprise privacy, code intelligence, and open tool interoperability:

### 1. Offline & Air-Gapped AI Inference (Local Ollama)
- **Local Provider Strategy**: `OllamaProvider(AIProvider)` connects to `http://localhost:11434` supporting `llama3`, `mistral`, `qwen2.5`, `phi3`, and `deepseek-r1`.
- **Zero Cloud Telemetry**: When configured in `local` mode, all cloud API calls (OpenRouter, Gemini, OpenAI) are bypassed, providing guaranteed air-gapped security for sensitive enterprise research.
- **Automated Health Check**: Real-time probe of `/api/tags` detects local server availability and alerts the evaluator if `ollama serve` is not active.

### 2. Codebase & GitHub Repo Paper Generator (`DocumentAnalysisAgent`)
- **Topological Repo Decomposition**: Ingests public GitHub URLs (`https://github.com/owner/repo`) or local folder trees (via Chromium File System Access API).
- **Parallel Module Analysis**: Decomposes code repositories into architectural areas (topologies, state synchronization, concurrency patterns, and algorithmic complexity bounds).
- **Formal Paper Output**: Synthesizes formal research papers and architecture specifications with citations and module diagrams.

### 3. Model Context Protocol (MCP) Plugin Extension Point
- **`PluginAgent` Base Class**: Standard interface wrapping Model Context Protocol tool servers to allow pluggable agent capabilities.
- **Dynamic `MCPPluginRegistry`**: Discovers and routes agent tasks to external MCP servers via JSON-RPC 2.0.
- **Reference Implementation (`AcademicDOIVerifierPlugin`)**: Connects to academic registry MCP servers to cross-verify DOIs against ACM Digital Library, arXiv, and Crossref.

---

## 📁 Repository Structure

```text
quorum/
├── apps/
│   ├── web/                    # Next.js 14 frontend (App Router, Tailwind, Zustand)
│   │   ├── src/app/            # App Router pages (/reports/[id], /sign-in, /sign-up)
│   │   ├── src/components/     # UI primitives, pipeline visualization, report views
│   │   ├── src/hooks/          # useReportEvents (WebSocket), useProjects, useReports
│   │   └── src/lib/            # Typed API client with auto-attaching auth headers
│   └── api/                    # FastAPI backend
│       ├── alembic/            # Database schema migrations
│       ├── src/agents/         # Multi-agent orchestration engine, DAG, providers, and MCP plugins
│       ├── src/api/            # REST API routers (/projects, /reports, /health)
│       ├── src/core/           # Circuit breaker, Redis client, rate limiter, security
│       ├── src/db/             # SQLAlchemy 2.0 async declarative models and sessions
│       ├── src/services/       # GitHub connector and external ingestion pipelines
│       ├── src/workers/        # Arq background worker and command queue
│       └── tests/              # Pytest suite covering full multi-agent DAG and Lane F plugins
├── packages/
│   └── shared-types/           # TypeScript types shared between web and tooling
├── infra/
│   ├── docker-compose.yml      # Infrastructure service definitions
│   └── migrations/             # Database migration artifacts
├── .env.example                # Canonical environment variable template
├── Procfile                    # Production process definitions (web, worker, release)
└── README.md                   # Project documentation
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
