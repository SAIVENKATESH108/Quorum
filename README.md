# Quorum

> **Autonomous multi-agent research and intelligence synthesis platform.**  
> Transforms research inquiries, GitHub repositories, and local codebases into structured, verifiable intelligence reports using parallel agent swarms.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌐 Production Deployment Status

> **Notice**: Security and deployment verification is in progress following production deployment configuration correction.

---

## 🎯 The Problem It Solves

Standard foundation model interfaces struggle with structured, long-form technical research:
1. **Single-Turn Blindness**: Monolithic prompt-completion paradigms lack the architectural structure to investigate orthogonal sub-problems in parallel.
2. **Unchecked Citations**: Generative models frequently invent non-existent DOIs, broken URLs, and hallucinated academic references.
3. **Opaque Synthesis**: Analysts have limited visibility into how conclusions were formed, which evidence was verified, and where contradictions were resolved.
4. **Analyst Bottleneck**: Knowledge workers spend tens of hours searching literature, aggregating disparate sources, and drafting structured documents.

**Quorum** addresses this by modeling research as an **asynchronous distributed multi-agent Directed Acyclic Graph (DAG)**. Parallel researcher workers, adversarial fact-checkers, and synthesis writers collaborate to produce structured reports backed by verifiable citations and exported publication-grade PDFs.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client Layer ["Client Layer (Edge & Browser)"]
        Browser["User Browser / Guest Judge UI"]
    end

    subgraph Edge Layer ["Frontend Edge Hosting (Vercel)"]
        NextWeb["Next.js 14 App Router<br/>(React Server Components + Zustand + TanStack Query)"]
        EdgeAuth["Session Middleware<br/>(Route Protection & Session Cookie Handling)"]
    end

    subgraph Backend Layer ["Backend Cluster (Railway / ASGI)"]
        ReverseProxy["Reverse Proxy / SSL Termination<br/>(Proxy Headers & WebSocket Routing)"]
        FastAPI["FastAPI ASGI Server (Uvicorn)<br/>(Tenant Scoping, Report Pipeline, Diagnostics)"]
        Worker["Async Arq Worker Service<br/>(Multi-Agent DAG Execution Swarm)"]
    end

    subgraph State & Bus Layer ["Managed Cloud Infrastructure"]
        Postgres[("PostgreSQL 16 with pgvector<br/>(Relational Models, Vectors, Ownership Scoping)")]
        RedisPubSub[("Redis 7<br/>(Task Queue Broker & Pub/Sub Event Streaming)")]
    end

    Browser -->|"HTTPS (REST)"| NextWeb
    Browser -->|"WSS WebSocket (?token=)"| ReverseProxy
    NextWeb --> EdgeAuth
    EdgeAuth -->|"Forward with Session Cookie / Bearer"| ReverseProxy
    ReverseProxy -->|"Proxy Headers"| FastAPI
    ReverseProxy -->|"WebSocket Upgrade"| FastAPI
    FastAPI -->|"Database Authentication / Scoped Queries"| Postgres
    FastAPI -->|"Enqueue AgentTaskCommand"| RedisPubSub
    Worker -->|"Pop Tasks & Run Agent Swarm"| RedisPubSub
    Worker -->|"Dual-Write Sections & Source Citations"| Postgres
    Worker -->|"Publish StatusEvent (report:{id}:events)"| RedisPubSub
    RedisPubSub -->|"Broadcast Live Telemetry"| FastAPI
    FastAPI -->|"Forward Live JSON Frame"| Browser
```

---

## 🧠 Multi-Agent Orchestration & AI Provider Layer

Quorum's research engine operates as an asynchronous pipeline governed by **Strategy**, **Factory**, and **Command** patterns:

### 1. Topological Multi-Agent DAG
```text
                  [Research Query / Ingestion Target]
                                   │
                         ┌─────────▼─────────┐
                         │ OrchestratorAgent │  (Decomposes inquiry into orthogonal subtopics)
                         └─────────┬─────────┘
                                   │
                     ┌─────────────┼─────────────┐   (Concurrent asyncio.gather wavefront)
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
                         │    WriterAgent    │  (Structured report synthesis & verified [n] citations)
                         └─────────┬─────────┘
                                   ▼
                    [Publication-Grade Report & PDF]
```

1. **OrchestratorAgent**: Decomposes inquiries into mutually exclusive subtopics and compiles an execution task graph.
2. **ResearcherAgent Swarm**: Dispatches concurrent workers to explore relevant literature, extract empirical findings, and bind primary source references.
3. **FactCheckerAgent**: Acts as a verification barrier. Evaluates extracted assertions, detects conflicting claims, checks domain heuristics, and assigns confidence scores.
4. **WriterAgent**: Synthesizes verified findings into clean, ordered report sections featuring interactive numerical citations linked to the bibliography.

### 2. Provider Strategy & Isolation Model

Execution providers are abstracted behind the `AIProvider` strategy interface with strict mode separation:

* **Cloud Multi-Provider Chain (`mode="cloud"`) — Status: Verified UI & Generation Workflow**:
  * Default production fallback: OpenRouter → Gemini → OpenAI.
  * Circuit breaker tracks consecutive failures (trips to `OPEN` for 60s cooldown; attempts `HALF_OPEN` canary).
  * Jittered exponential backoff for transient network and rate-limit errors.
* **Local Offline Inference (`mode="local"`) — Status: Verified Selectable Local Mode**:
  * Connects to local Ollama (`http://localhost:11434`) for air-gapped environments with zero cloud telemetry.
* **Evorozen Neural Pulse (`mode="neural_pulse"`) — Status: Mocked-Contract Verified; Live Run Pending Credential**:
  * Dedicated selectable provider mode.
  * **Strict Isolation**: Neural Pulse is completely excluded from the default cloud fallback chain; choosing Cloud mode never invokes Neural Pulse, and explicit Neural Pulse mode never silently falls back to other providers.
  * **Strict Contract**: Enforces the 2,000-character prompt limit; sends clean minimal payloads (`action_type: "chat"`, `prompt`); omits unsupported parameters.
  * **Quota Guardrails**: Quota exhaustion is non-transient and rejects immediate retries without retry storms. Zero outbound network probes are made for status checks.

---

## 💻 Tech Stack & Architecture

| Layer | Technology | Architectural Role |
|---|---|---|
| **Frontend Framework** | **Next.js 14 (App Router)** | React Server Components for initial rendering, dynamic routing, and typed client interactions. |
| **Design & Theming** | **Tailwind CSS + CSS Variables** | Custom tokenized design system (`bg-bg`, `bg-surface`, `text-text-primary`, `accent`) with persistent light/dark themes. |
| **State Management** | **Zustand + TanStack Query** | Zustand for ephemeral UI drawer/modal state; TanStack Query for server cache, pagination, and polling. |
| **Backend Framework** | **FastAPI (Python 3.11+)** | High-throughput ASGI server with Pydantic v2 schemas and native OpenAPI generation. |
| **Database & Vectors** | **PostgreSQL 16 with `pgvector`** | Relational integrity for users, projects, reports, and sources with vector similarity support. |
| **Asynchronous Queue** | **Redis 7 + Arq** | Asynchronous task queue for long-running multi-agent pipelines and real-time event broadcasting. |
| **Authentication** | **Native Database Auth (Argon2id + JWT)** | Cookie-backed (`quorum_session`) and bearer authentication with strict tenant boundary enforcement and 1-Click Guest Judge access. |

---

## 🔒 Access Policy & Authorization Model

Quorum implements a **failure-closed, tenant-isolated workspace model**:

* **Authenticated Workspace Views**: Routes (`/projects`, `/reports`, `/sources`, `/agents`, `/settings`) require authenticated sessions. Unauthenticated visitors are safely redirected to `/sign-in`.
* **Guest Judge Demo Experience**: Evaluators can enter via the one-click `"Enter as Guest Judge"` action on `/sign-in`. This establishes an ephemeral, read-only session with a dedicated `Guest Judge — Read-only` banner. All write mutations (`POST`, `PATCH`, `DELETE`) return HTTP 403 Forbidden.
* **Curated Demo Visibility**: Guest Judges view strictly curated demo resources (projects and reports marked with `is_guest_demo=true`). Private user workspaces remain completely inaccessible.
* **Public Report Showcase**: Explicitly curated complete demo reports and their publication-grade PDFs are accessible to anonymous visitors without login. Private owner reports and their PDFs require authentication and reject unauthenticated requests with HTTP 401 and cross-tenant requests with HTTP 403.
* **Tenant Isolation**: Database queries enforce ownership at the SQL level (`project.user_id == current_user.id`). Authenticated non-owners cannot view, mutate, or export another tenant's reports.
* **Admin Verification**: Administrative capabilities (system diagnostics and demo curation) require verified admin credentials. System diagnostics mask internal database host details and leak zero passwords or credentials.

---

## 📊 Verified Capabilities & Technical Assertions

The following capabilities have been validated through end-to-end regression suites and multi-identity walkthroughs:

- **Multi-Agent Research Pipeline**: Multi-agent research pipeline with report generation.
- **Verified DOI Citation Workflow**: Verified DOI citation workflow for free-text research reports.
- **Per-Report PDF Export**: Per-report PDF export with report-specific content.
- **Public Showcase**: Public showcase for explicitly curated complete demo reports.
- **Protected Authenticated Workspace**: Protected authenticated workspace with owner/non-owner isolation.
- **Guest Judge Workspace**: Guest Judge read-only demo workspace.
- **Repository Ingestion**: GitHub/local-folder RAG ingestion with grounded repository/file citations.
- **Report & Source Data Wiring**: Report/source data wiring with scoped totals and pagination.
- **Test Database Guardrails**: Isolated test database guardrails preventing automated tests from writing to production.
- **Neural Pulse Provider Integration**: Neural Pulse provider integration implemented and mocked-test verified.

---

## ⚠️ Required Limitations & Scope Disclaimers

To maintain strict technical documentation integrity, the following limitations are explicitly declared:

1. **Neural Pulse Live Generation**: Neural Pulse live report generation is not verified because the prior credential is retired/quota-exhausted.
2. **Automated Browser Runner**: Automated Playwright browser-driver validation was unavailable due to external driver download failure; manual browser verification was performed instead.
3. **Academic-Domain Source Classification**: Academic-domain source classification is a URL-domain heuristic, not verified peer-review metadata.
4. **Secret Scrubbing**: Pattern-based secret scrubbing is assistive and cannot guarantee detection of all confidential information.
5. **Repository Indexing**: Repository indexing may be partial when file limits, excluded file types, or repository tree truncation apply.
6. **Guest Judge Scope**: Guest Judge view exposes only curated demo resources.

> **Explicit Negative Declarations**:
> Quorum explicitly does **not** claim:
> * Fully IEEE compliant
> * Guaranteed hallucination-free
> * Guaranteed secure
> * All research databases searched
> * Neural Pulse live generation verified
> * All reports publicly accessible
> * All sources peer-reviewed
> * Plagiarism-free
> * Legally safe
> * Patent/novelty verified

---

## 🧪 Running Automated Tests

Quorum enforces test isolation guardrails to guarantee automated tests never write to production data:

```bash
cd apps/api
ENVIRONMENT=test python -m pytest tests/ -v -W error::RuntimeWarning
```

> **Test Suite Evidence**: 102 automated tests passed with no failures and no runtime warnings (`-W error::RuntimeWarning` enforced). Two upstream framework deprecation warnings were observed from dependencies (`StarletteDeprecationWarning` and `anyio.abc.BlockingPortal` deprecation warning). Production database aggregate counts remained invariant (zero deltas) before and after test execution.

---

## 🛠️ Step-by-Step Local Setup

### Prerequisites
* **Node.js**: `v20.x` or later (tested on Node `v24+`) and `npm`
* **Python**: `3.11+` (with virtual environment or `uv`)
* **Docker & Docker Compose**: For local PostgreSQL with `pgvector` and Redis
* **Git**

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/quorum.git
cd quorum
```

### 2. Configure Environment Variables
Copy the root `.env.example` template:
```bash
cp .env.example .env
```
Configure your database connection, Redis URL, server secret, and optional AI provider credentials:
```ini
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/quorum
REDIS_URL=redis://localhost:6379/0

# Cloud Inference Providers
OPENROUTER_API_KEY=your_openrouter_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
NEURAL_PULSE_API_KEY=

# Authentication Secret
AUTH_SECRET_KEY=replace_with_a_long_random_server_secret
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 3. Start Infrastructure
```bash
docker compose up -d postgres redis
```

### 4. Run Migrations
```bash
cd apps/api
python -m venv .venv
# On Windows: .venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate
pip install -e .
alembic upgrade head
```

### 5. Launch Backend Server
```bash
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```
Verify health:
```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

### 6. Launch Asynchronous Worker
In a separate terminal with virtual environment active:
```bash
cd apps/api
python -m src.workers.main
```

### 7. Launch Frontend
In a separate terminal:
```bash
cd apps/web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📁 Repository Structure

```text
quorum/
├── apps/
│   ├── web/                    # Next.js 14 App Router frontend
│   │   ├── src/app/            # Routes: Landing, Dashboard, Reports, Sources, Sign-In
│   │   ├── src/components/     # UI design system, pipeline diagrams, cards, badges
│   │   ├── src/hooks/          # Query hooks (useProjects, useReports, useProvidersStatus)
│   │   └── src/lib/            # Type-safe API client and session management
│   └── api/                    # FastAPI ASGI backend
│       ├── alembic/            # Database schema migrations
│       ├── src/agents/         # Multi-agent DAG engine, providers, and task definitions
│       ├── src/api/            # REST endpoints (auth, projects, reports, sources, admin)
│       ├── src/core/           # Circuit breaker, rate limiting, and security dependencies
│       ├── src/db/             # Declarative SQLAlchemy models and session management
│       ├── src/workers/        # Arq background worker and streaming publishers
│       └── tests/              # 102-test automated regression suite
├── docs/                       # System documentation and architecture specifications
├── .env.example                # Canonical environment variable template
├── docker-compose.yml          # Local container service definitions
└── README.md                   # System documentation
```

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
