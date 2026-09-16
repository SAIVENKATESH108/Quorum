# 🎬 Quorum — 3-Minute Video Demo Script & Screenplay

**Target Length**: Exactly 3:00 (180 seconds)  
**Primary Audience**: Hackathon Judges, Investors, and Technical Evaluators  
**Speaker**: Founder / Lead Engineer  

---

## Breakdown by Section

```text
┌───────────────┬─────────────────────────────────────────────────┬──────────┐
│ Timestamp     │ Stage / Topic                                   │ Duration │
├───────────────┼─────────────────────────────────────────────────┼──────────┤
│ 0:00 - 0:20   │ 1. The Problem                                  │ 20s      │
│ 0:20 - 0:50   │ 2. Query Submission & Live Pipeline (Money Shot)│ 30s      │
│ 0:50 - 1:50   │ 3. Completed Report & Cryptographic Citations   │ 60s      │
│ 1:50 - 2:30   │ 4. Go-To-Market (GTM) Strategy & Wedge          │ 40s      │
│ 2:30 - 3:00   │ 5. Technical Architecture for Judges            │ 30s      │
└───────────────┴─────────────────────────────────────────────────┴──────────┘
```

---

### [0:00 – 0:20] 1. The Problem (20 Seconds)

**Visuals**:
* Camera on speaker or split screen showing a frustrated analyst with 40 browser tabs open (Google Scholar, arXiv, Twitter/X research threads).
* Cut to a ChatGPT/Perplexity interface outputting hallucinations and broken citations.

**Voiceover**:
> *"When investors, researchers, or strategy teams need deep technical intelligence, modern AI fails them. Standard LLMs hallucinate facts, fabricate source links, and collapse when forced to synthesize complex, multi-variable topics. Analysts end up spending 15 to 20 hours manually cross-referencing papers, verifying claims, and drafting reports.  
> Research isn't a conversational prompt—it’s an engineering pipeline. Meet **Quorum**."*

---

### [0:20 – 0:50] 2. Query Submission & Live Pipeline Visualization (30 Seconds — The Money Shot)

**Visuals**:
* Screen recording of the **Quorum** Dashboard ([`/reports/new`](https://quorum-research.vercel.app/reports/new)).
* User types query: `"Analyze consensus mechanisms in distributed ledger systems: compare PBFT, Raft, and Narwhal DAG algorithms."`
* Clicks **"Deploy Agent Swarm"**.
* Instant redirect to the live dashboard ([`/reports/[reportId]`](https://quorum-research.vercel.app/reports/rep-1)).
* **Camera zooms in on the Pipeline**:
  * Top status pulses from `Planning` to `Researching`.
  * The parallel research swarm card expands, revealing 3 active worker sub-cards:
    * *Worker 1: FLP Impossibility & Asynchronous Bounds* (pulsing spinner, live claims incrementing: `8 claims`).
    * *Worker 2: Byzantine Quorums & Partial Synchrony* (live claims: `12 claims`).
    * *Worker 3: DAG Consensus & Narwhal Mempools* (live claims: `10 claims`).
  * Live activity feed streaming real-time WebSocket events on the right.

**Voiceover**:
> *"Watch what happens when we submit a query. Within milliseconds, our Orchestration Engine decomposes the topic into an asynchronous Directed Acyclic Graph.  
> Right here is the money shot: we don't query one model linearly. We dispatch a parallel swarm of independent Researcher Agents concurrently. Each agent investigates orthogonal sub-domains, harvests primary literature, and extracts verifiable claims simultaneously.  
> Live WebSocket telemetry streams every state transition directly to the client without a single page reload."*

---

### [0:50 – 1:50] 3. The Completed Report & Citations (60 Seconds)

**Visuals**:
* The Fact-Checking stage lights up green (`Confidence: 94%`, `0 contradictions detected`).
* The Writing stage synthesizes the report.
* Screen smoothly reveals the completed institutional-grade report via a spring animation.
* Cursor scrolls through structured sections: *Executive Summary*, *Comparative Latency Bounds*, *Byzantine Resilience*.
* Cursor hovers over inline numerical citations `[1]`, `[2]`, `[3]`.
* Clicking `[2]` smoothly scrolls down to the **"Cited Sources & Academic Literature"** panel, highlighting the peer-reviewed paper title, primary URL, publication year, and relevance badge.
* Shows the "Copy Markdown" and "Download PDF" action buttons.

**Voiceover**:
> *"Notice the synchronization barrier: once research completes, an adversarial Fact-Checker agent cross-examines every single claim, checks for contradictions, and scores claim veracity.  
> The result? A pristine, multi-page intelligence report. Not generic AI fluff—a structured executive document.  
> Look at the citations: every factual assertion is linked to an exact numerical footnote. When I click citation `[2]`, it jumps directly to the peer-reviewed literature in our bibliography—with paper authors, arXiv DOIs, and relevance tags. Every claim is verifiable down to the primary source."*

---

### [1:50 – 2:30] 4. Go-To-Market Pitch & Wedge (40 Seconds)

**Visuals**:
* Clean slide/graphic overlay showing:
  * **Target Persona**: Web3 & AI Venture Capital Funds, Corporate Strategy Teams, Equity Research Desks.
  * **The Wedge**: The "10-Minute Diligence Memo" for investment committees.
  * **Traction & Distribution**: Chrome extension for arXiv/Crunchbase + API integrations into Slack/Notion.
* Quick cut back to the Quorum workspace displaying multiple saved projects.

**Voiceover**:
> *"Our Go-To-Market strategy is laser-focused. Our wedge is the '10-Minute Diligence Memo' for venture capital analysts and institutional research desks who evaluate dozens of technical whitepapers each week.  
> Instead of burning days drafting initial investment memos, analysts deploy Quorum to generate comprehensive technical baselines in 4 minutes.  
> We reach them bottom-up through open research communities on X and Farcaster, coupled with direct integrations into their existing workflows across Notion, Slack, and Chrome. Once analysts experience cited, multi-agent synthesis, they never go back to blank documents."*

---

### [2:30 – 3:00] 5. Technical Architecture for Judges (30 Seconds)

**Visuals**:
* Display the Mermaid system architecture diagram from the README.
* Highlight the decoupling: Vercel frontend, Railway/Fly.io ASGI backend, separate Arq worker process, Neon Postgres with `pgvector`, and Redis Pub/Sub.
* Quick terminal cut showing test suite passing with `alembic upgrade head`.

**Voiceover**:
> *"For the technical judges reviewing our codebase: Quorum is engineered for enterprise reliability.  
> Our backend runs FastAPI with strict Pydantic schemas, backed by managed PostgreSQL on Neon with `pgvector` for semantic literature search.  
> Long-running LLM tasks never block HTTP threads—they're enqueued to a dedicated Arq worker swarm over Redis.  
> Our AI strategy layer wraps Claude, GPT, and Neural Pulse in circuit breakers with exponential backoff and automatic provider fallbacks.  
> Frontend is Next.js 14 on Vercel with Clerk edge route protection.  
> Quorum is live, public, and open-source today. Thank you!"*

---

## 🎙️ Recording Tips & Checklist

1. **Resolution**: 1920x1080 (1080p) or 4K at 60fps.
2. **Audio**: Clean condenser mic with noise suppression (no background hiss).
3. **Pacing**: Speak authoritatively at a steady 140–150 words per minute.
4. **Browser Setup**: Clear tabs, hide bookmarks bar, use dark theme to highlight the neon status badges.
5. **Interactive Demo Links**: Keep `https://quorum-research.vercel.app` open in one tab and `https://api.quorum-research.up.railway.app/docs` open in another for quick switching.
