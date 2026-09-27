# 🎬 Quorum — 3-Minute Video Demo Script & Screenplay

**Target Length**: Exactly 3:00 (180 seconds)  
**Primary Audience**: Hackathon Judges, Technical Evaluators, and Researchers  
**Speaker**: Lead Engineer  

---

## Breakdown by Section

```text
┌───────────────┬─────────────────────────────────────────────────┬──────────┐
│ Timestamp     │ Stage / Topic                                   │ Duration │
├───────────────┼─────────────────────────────────────────────────┼──────────┤
│ 0:00 - 0:20   │ 1. The Problem                                  │ 20s      │
│ 0:20 - 0:50   │ 2. Query Submission & Live Pipeline             │ 30s      │
│ 0:50 - 1:50   │ 3. Completed Report & Verified Citations        │ 60s      │
│ 1:50 - 2:30   │ 4. Evaluation Workflow & Multi-Tenant Security  │ 40s      │
│ 2:30 - 3:00   │ 5. Technical Architecture & Verified Extensions │ 30s      │
└───────────────┴─────────────────────────────────────────────────┴──────────┘
```

---

### [0:00 – 0:20] 1. The Problem (20 Seconds)

**Visuals**:
* Camera on speaker or split screen showing an analyst overwhelmed by 40 browser tabs (arXiv, technical docs, repositories).
* Quick cut highlighting LLM hallucination: conversational models inventing broken citations and non-existent DOIs.

**Voiceover**:
> *"When technical teams, analysts, or researchers need deep intelligence, conversational AI models fall short. Monolithic prompts struggle to explore multi-variable domains in parallel, often fabricating DOIs and citations. Researchers still spend tens of hours searching literature, aggregating sources, and drafting structured documents.  
> Rigorous research isn't a conversational prompt—it’s an asynchronous engineering pipeline. Meet **Quorum**."*

---

### [0:20 – 0:50] 2. Query Submission & Live Pipeline Visualization (30 Seconds)

**Visuals**:
* Screen recording of the **Quorum** New Report interface (`/reports/new`).
* User types research query: `"Analyze consensus mechanisms in distributed ledger systems: compare PBFT, Raft, and Narwhal DAG algorithms."`
* Selects **Cloud Multi-Provider Swarm**.
* Clicks **"Launch Multi-Agent Synthesis Swarm"**.
* Navigation to the live dashboard view.
* **Camera focuses on Pipeline Visualization**:
  * Status transitions through pipeline stages: `Planning` → `Researching` → `Fact-Checking` → `Writing`.
  * The parallel researcher swarm card displays active concurrent workers.
  * Real-time WebSocket activity feed streaming status frames.

**Voiceover**:
> *"Watch what happens when we submit a query. Within milliseconds, our Orchestration Engine decomposes the inquiry into an asynchronous Directed Acyclic Graph.  
> Rather than a linear prompt, Quorum dispatches a parallel swarm of independent Researcher Agents concurrently. Each worker explores orthogonal sub-domains, harvests primary literature, and extracts verifiable claims simultaneously.  
> Real-time WebSocket telemetry streams every state transition directly to the client."*

---

### [0:50 – 1:50] 3. The Completed Report & Citations (60 Seconds)

**Visuals**:
* The Fact-Checking stage completes with confidence metrics and zero contradiction flags.
* The Writing stage synthesizes the report.
* Screen displays the completed structured report.
* Cursor scrolls through ordered sections: *Executive Summary*, *Comparative Latency Bounds*, *Byzantine Resilience*.
* Cursor hovers over interactive inline numerical citations `[1]`, `[2]`, `[3]`.
* Clicking `[2]` scrolls smoothly down to the **"Cited Sources & Academic Literature"** bibliography panel, displaying the source URL domain, title, and citation anchor.
* Shows the "Export PDF" action button.
* Opens the downloaded PDF: multi-page document with headers, section numbering, and citation tables.

**Voiceover**:
> *"Notice the verification barrier: once research workers finish, an adversarial Fact-Checker agent cross-examines claims and evaluates source evidence.  
> The result is a structured, sectioned intelligence report.  
> Look at the citations: factual claims are linked to exact numerical references. Clicking a citation jumps down to the verified source bibliography with source URLs, domains, and relevance details.  
> With one click, researchers can export a publication-grade PDF containing the exact synthesized findings."*

---

### [1:50 – 2:30] 4. Evaluation Workflow & Multi-Tenant Security (40 Seconds)

**Visuals**:
* Demonstration of the Sign-In page (`/sign-in`).
* Click **"Enter as Guest Judge"** button.
* Dashboard appears with the prominent `Guest Judge — Read-only` badge.
* Navigates to `/projects` and `/reports`: strictly curated demo resources are visible; private tenant projects remain hidden.
* Clicks write action: clear read-only prohibition (HTTP 403 enforcement).
* Switches between dark and light themes using the top-nav theme toggle.

**Voiceover**:
> *"For evaluators and judges, Quorum provides a seamless one-click Guest Judge mode.  
> Clicking 'Enter as Guest Judge' creates an ephemeral, read-only session. Evaluators can explore curated demo projects, review completed reports, filter by status, and inspect harvested sources.  
> Tenant boundaries are enforced strictly in the database: private owner workspaces are completely isolated from non-owners and guest evaluators, while write actions are securely blocked for guest sessions."*

---

### [2:30 – 3:00] 5. Technical Architecture & Verified Extensions (30 Seconds)

**Visuals**:
* Display the system architecture diagram: Next.js 14 frontend, FastAPI ASGI backend, asynchronous Arq worker, PostgreSQL 16 with `pgvector`, and Redis.
* Highlight provider flexibility: Cloud multi-provider fallback (OpenRouter, Gemini, OpenAI), local offline inference via Ollama, and isolated Neural Pulse integration.
* Brief cut showing the 102 automated tests passing against an isolated test environment with zero production database writes.

**Voiceover**:
> *"Under the hood, Quorum is built for resilience.  
> Our backend runs FastAPI with strict Pydantic schemas, backed by PostgreSQL with pgvector and Redis task queues.  
> Our AI provider layer isolates cloud fallback chains from dedicated modes like offline Ollama and Evorozen Neural Pulse.  
> Our 102-test automated regression suite enforces rigorous database isolation, ensuring test runs never modify production data.  
> Quorum is live, verified, and open-source today. Thank you!"*

---

## 🎙️ Recording Tips & Checklist

1. **Resolution**: 1920x1080 (1080p) at 60fps.
2. **Audio**: Clean microphone with background noise suppression.
3. **Pacing**: Steady, authoritative cadence (~140 words per minute).
4. **Theme**: Clean dark or light mode with high-contrast text and status badges.
5. **Safety**: Ensure no internal emails, database URLs, full internal UUIDs, or secret keys appear on screen.
