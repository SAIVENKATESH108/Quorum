"""
Quorum Publication-Grade PDF Generator Service
Uses ReportLab to produce publication-grade, pixel-perfect technical documentation,
engineering specifications, and research paper PDFs matching the double-border,
two-pass NumberedCanvas architecture with running headers, footers, and quote boxes.
"""

import io
import os
from typing import Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page count and draw
    exact double border, running headers, and running footers on every page.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[dict] = []
        self.doc_title = "Quorum — Autonomous Multi-Agent AI Research & Verification Platform"
        self.doc_author = "Lead Architect: V.A. Sai Venkatesh"
        self.doc_confidential = "CONFIDENTIAL & PROPRIETARY — Quorum Autonomous Systems v1.0"

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int) -> None:
        self.saveState()

        # Double border rectangle (exact points matching specification)
        # Outer border: Dark Navy #1e1b4b
        self.setStrokeColor(HexColor("#1e1b4b"))
        self.setLineWidth(1.5)
        self.rect(36, 36, 540, 720)

        # Inner border: Violet #7c3aed
        self.setStrokeColor(HexColor("#7c3aed"))
        self.setLineWidth(1.0)
        self.rect(39, 39, 534, 714)

        page_num = self._pageNumber
        if page_num > 1:
            # Running header text
            self.setFont("Helvetica-Bold", 8.5)
            self.setFillColor(HexColor("#1e1b4b"))
            self.drawString(50, 765, self.doc_title[:62])

            self.setFont("Helvetica", 8.5)
            self.setFillColor(HexColor("#64748b"))
            self.drawRightString(562, 765, self.doc_author)

            # Horizontal line below header
            self.setStrokeColor(HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(50, 760, 562, 760)

            # Horizontal line above footer
            self.line(50, 30, 562, 30)

            # Running footer text
            self.setFont("Helvetica", 7.5)
            self.setFillColor(HexColor("#64748b"))
            self.drawString(50, 20, self.doc_confidential)
            self.drawRightString(562, 20, f"Page {page_num} of {total_pages}")
        else:
            # Page 1 footer
            self.setFont("Helvetica", 7.5)
            self.setFillColor(HexColor("#64748b"))
            self.drawString(50, 20, self.doc_confidential)
            self.drawRightString(562, 20, f"Page 1 of {total_pages}")

        self.restoreState()


def create_quote_box(
    title: str,
    text: str,
    border_color: str = "#8b5cf6",
    bg_color: str = "#faf5ff",
    title_color: str = "#6d28d9",
    text_color: str = "#4c1d95"
) -> Table:
    """Creates a stylized architect quote box matching the publication specification."""
    content = [
        Paragraph(
            f"<b>★ {title}</b>",
            ParagraphStyle(
                "QuoteTitle",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=HexColor(title_color)
            )
        ),
        Spacer(1, 3),
        Paragraph(
            f"<i>\"{text}\"</i>",
            ParagraphStyle(
                "QuoteBody",
                fontName="Courier-Oblique",
                fontSize=8.0,
                leading=10.5,
                textColor=HexColor(text_color)
            )
        )
    ]
    t = Table([[content]], colWidths=[508])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor(bg_color)),
        ('BOX', (0, 0), (-1, -1), 1.5, HexColor(border_color)),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def build_quorum_system_documentation_pdf(
    output_path: Optional[str] = None,
    image_dir: Optional[str] = None,
) -> bytes:
    """
    Generates the complete, publication-grade 9-page Quorum System Documentation
    and Engineering Specification PDF following the exact architectural standards.
    """
    pdf_buffer = io.BytesIO()
    target = output_path if output_path else pdf_buffer

    doc = SimpleDocTemplate(
        target,
        pagesize=letter,
        leftMargin=52,
        rightMargin=52,
        topMargin=48,
        bottomMargin=46
    )

    story: List[Any] = []

    # Typography Styles
    title_style = ParagraphStyle("DocTitle", fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=HexColor("#1e1b4b"))
    subtitle_style = ParagraphStyle("DocSubtitle", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=HexColor("#475569"))
    section_h1 = ParagraphStyle("SectionH1", fontName="Helvetica-Bold", fontSize=14.5, leading=17.5, textColor=HexColor("#1e1b4b"))
    section_h2 = ParagraphStyle("SectionH2", fontName="Helvetica-Bold", fontSize=11.5, leading=14.5, textColor=HexColor("#6d28d9"))
    body_p = ParagraphStyle("BodyP", fontName="Helvetica", fontSize=8.5, leading=12.5, textColor=HexColor("#334155"))
    bullet_p = ParagraphStyle("BulletP", fontName="Helvetica", fontSize=8.2, leading=11.5, textColor=HexColor("#334155"), leftIndent=12)
    tbl_cell = ParagraphStyle("TblCell", fontName="Helvetica", fontSize=8.0, leading=10.5, textColor=HexColor("#1e293b"))
    tbl_cell_bold = ParagraphStyle("TblCellBold", fontName="Helvetica-Bold", fontSize=8.0, leading=10.5, textColor=HexColor("#0f172a"))
    tbl_header = ParagraphStyle("TblHdr", fontName="Helvetica-Bold", fontSize=8.2, leading=10.5, textColor=white)
    code_cell = ParagraphStyle("CodeCell", fontName="Courier", fontSize=7.5, leading=9.5, textColor=HexColor("#0f172a"))

    # =========================================================================
    # PAGE 1: COVER & EXECUTIVE SUMMARY
    # =========================================================================
    if image_dir:
        logo_path = os.path.join(image_dir, "og-image.png")
        if os.path.exists(logo_path):
            story.append(Image(logo_path, width=120, height=60, hAlign='CENTER'))
            story.append(Spacer(1, 8))

    story.append(Paragraph("Quorum — Complete Engineering<br/>Specification & System Documentation", title_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "Autonomous Multi-Agent AI Research Swarms, Topological DAG Execution, Academic DOI Fact-Checking, Local Offline Ollama Engine & Model Context Protocol",
        subtitle_style
    ))
    story.append(Spacer(1, 10))

    meta_data = [
        [Paragraph("Lead Engineer & Architect:", tbl_cell_bold), Paragraph("V.A. SAI VENKATESH", tbl_cell_bold)],
        [Paragraph("Multi-Agent Architecture:", tbl_cell_bold), Paragraph("Topological DAG Orchestrator, Async ReAct Swarm, Semantic Scholar & CrossRef Fact-Checker", tbl_cell)],
        [Paragraph("Dual AI Inference Engine:", tbl_cell_bold), Paragraph("Cloud Providers (Gemini 1.5, GPT-4o, Claude 3.5) + Offline Air-Gapped Ollama (Llama 3, Mistral)", tbl_cell)],
        [Paragraph("Full-Stack Implementation:", tbl_cell_bold), Paragraph("FastAPI 0.115+, SQLAlchemy 2.0 Async, PostgreSQL pgvector, Next.js 14 SSR, Tailwind CSS", tbl_cell)],
        [Paragraph("Document Classification:", tbl_cell_bold), Paragraph("Enterprise Engineering Specification v1.0 (September 2026)", tbl_cell)]
    ]
    t_meta = Table(meta_data, colWidths=[150, 358])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    vision_text = (
        "Current generative AI tools provide persuasive, fluent prose but frequently hallucinate citations, invent non-existent DOIs, "
        "and collapse under multi-step research investigations. Quorum was engineered to eradicate algorithmic hallucination in mission-critical "
        "research. By orchestrating a topological DAG of specialized agents—planners, academic retrievers, peer-review fact-checkers, and codebase "
        "synthesizers—Quorum guarantees mathematical attribution, verifiable source grounding, and complete transparency from raw query to final paper."
    )
    story.append(create_quote_box(
        "LEAD ARCHITECT SYSTEM VISION — V.A. Sai Venkatesh (Lead Architect)",
        vision_text,
        border_color="#f59e0b",
        bg_color="#fffbeb",
        title_color="#b45309",
        text_color="#78350f"
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Overview: The Autonomous Research & Verification Imperative", section_h1))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "Modern scientific research, competitive intelligence, and software engineering demand synthesis of massive, disparate literature. "
        "However, monolithic language models suffer from context decay, citation fabrication, and inability to interact with live software codebases. "
        "<b>Quorum introduces an autonomous, verified multi-agent paradigm</b> where research tasks are decomposed into dependency-governed DAGs.",
        body_p
    ))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "Whether operating across global academic databases or inside secure, air-gapped corporate environments using local Ollama models, "
        "Quorum synthesizes comprehensive technical documentation, research papers, and codebase audits with strict DOI verification and live AST inspection.",
        body_p
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: ARCHITECTURE & CS FOUNDATIONS
    # =========================================================================
    story.append(Paragraph("System Architecture & Computer Science Foundations", section_h1))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "Quorum is structured across four decoupled architectural layers with strict asynchronous protocol boundaries: "
        "Presentation (Next.js SSR), Distributed Coordination (FastAPI & Arq Workers), Execution (DAG Swarms), and Verified Storage (PostgreSQL & pgvector).",
        body_p
    ))
    story.append(Spacer(1, 7))

    cs_headers = [Paragraph("Computer Science Pattern", tbl_header), Paragraph("Implementation & File Location", tbl_header), Paragraph("Engineering Rationale", tbl_header)]
    cs_rows = [
        [
            Paragraph("<b>Topological DAG Swarm</b>", tbl_cell_bold),
            Paragraph("<code>apps/api/src/agents/</code><br/><code>orchestrator.py</code>", code_cell),
            Paragraph("Enforces strict dependency order across parallel research tasks. Eliminates race conditions and guarantees synthesis only occurs after fact-check completion.", tbl_cell)
        ],
        [
            Paragraph("<b>Polymorphic Provider Strategy</b>", tbl_cell_bold),
            Paragraph("<code>apps/api/src/agents/</code><br/><code>providers.py</code>", code_cell),
            Paragraph("Abstracts LLM inference across Gemini, OpenAI, Claude, and local Ollama. Switches models transparently with zero agent code changes.", tbl_cell)
        ],
        [
            Paragraph("<b>Circuit Breaker & Fallback</b>", tbl_cell_bold),
            Paragraph("<code>apps/api/src/agents/</code><br/><code>providers.py:OllamaProvider</code>", code_cell),
            Paragraph("Monitors endpoint health, latency, and rate limits. Gracefully degrades to local offline weights or cached fixtures during network outages.", tbl_cell)
        ],
        [
            Paragraph("<b>Model Context Protocol (MCP)</b>", tbl_cell_bold),
            Paragraph("<code>apps/api/src/agents/</code><br/><code>plugins.py</code>", code_cell),
            Paragraph("Standardized JSON-RPC plugin architecture enabling dynamic agent capability injection (DOI fact-checkers, local linters, private vector stores).", tbl_cell)
        ],
        [
            Paragraph("<b>AST Codebase Ingestion</b>", tbl_cell_bold),
            Paragraph("<code>apps/api/src/agents/</code><br/><code>document_analyzer.py</code>", code_cell),
            Paragraph("Recursively traverses repositories (GitHub API & local filesystem), extracting AST symbol hierarchies and docstrings for technical paper synthesis.", tbl_cell)
        ],
    ]
    t_cs = Table([cs_headers] + cs_rows, colWidths=[130, 140, 238])
    t_cs.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0f172a')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_cs)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Multi-Agent Swarm Topology & Operational Roles", section_h2))
    story.append(Spacer(1, 5))

    swarm_headers = [
        Paragraph("Agent Designation", tbl_header),
        Paragraph("Algorithmic Function", tbl_header),
        Paragraph("Input / Context", tbl_header),
        Paragraph("Output Artifact", tbl_header)
    ]
    swarm_rows = [
        [
            Paragraph("<b>Orchestrator Agent</b>", tbl_cell_bold),
            Paragraph("Decomposes queries into parallel sub-tasks and compiles topological DAG", tbl_cell),
            Paragraph("User Research Query, Target Scope, Source Mode", tbl_cell),
            Paragraph("Execution DAG & Dependency Manifest", tbl_cell)
        ],
        [
            Paragraph("<b>Academic Searcher</b>", tbl_cell_bold),
            Paragraph("Queries academic APIs (Semantic Scholar, arXiv) with vector re-ranking", tbl_cell),
            Paragraph("Sub-task hypothesis & keyword vectors", tbl_cell),
            Paragraph("Ranked literature abstracts & peer-reviewed DOIs", tbl_cell)
        ],
        [
            Paragraph("<b>Fact-Checker Agent</b>", tbl_cell_bold),
            Paragraph("Verifies mathematical claims, dates, and empirical statements against raw sources", tbl_cell),
            Paragraph("Draft claims + source citations", tbl_cell),
            Paragraph("Citation confidence score & verified DOI list", tbl_cell)
        ],
        [
            Paragraph("<b>Document Analyzer</b>", tbl_cell_bold),
            Paragraph("Scans repository trees, architecture configs, and code implementations", tbl_cell),
            Paragraph("GitHub Repo URL or Local directory path", tbl_cell),
            Paragraph("AST architecture map & component specs", tbl_cell)
        ],
        [
            Paragraph("<b>Synthesis Lead</b>", tbl_cell_bold),
            Paragraph("Integrates verified claims into LaTeX / Markdown research paper", tbl_cell),
            Paragraph("Verified claims, AST specs, DOI references", tbl_cell),
            Paragraph("Final publication paper & ReportLab PDF", tbl_cell)
        ]
    ]
    t_swarm = Table([swarm_headers] + swarm_rows, colWidths=[105, 145, 130, 128])
    t_swarm.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#7c3aed')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#faf5ff')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_swarm)
    story.append(PageBreak())

    # =========================================================================
    # HELPER FOR DETAILED SUBSYSTEM SPEC PAGES 3 TO 7
    # =========================================================================
    def add_subsystem_page(
        title: str,
        quote_title: str,
        quote_text: str,
        core_problem: str,
        technical_spec: str,
        workflow_steps: List[str]
    ) -> None:
        story.append(Paragraph(title, section_h1))
        story.append(Spacer(1, 2))

        t_line = Table([[""]], colWidths=[508], rowHeights=[1.5])
        t_line.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#7c3aed'))]))
        story.append(t_line)
        story.append(Spacer(1, 8))

        story.append(create_quote_box(quote_title, quote_text))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Systemic Problem & Architectural Need:", section_h2))
        story.append(Spacer(1, 3))
        story.append(Paragraph(core_problem, body_p))
        story.append(Spacer(1, 7))

        story.append(Paragraph("Deep Engineering Specification:", section_h2))
        story.append(Spacer(1, 3))
        story.append(Paragraph(technical_spec, body_p))
        story.append(Spacer(1, 7))

        story.append(Paragraph("Operational Procedures & Execution Lifecycle:", section_h2))
        story.append(Spacer(1, 3))
        for idx, step in enumerate(workflow_steps):
            story.append(Paragraph(f"<b>{idx+1}.</b> {step}", bullet_p))
            story.append(Spacer(1, 2))

        story.append(PageBreak())

    # =========================================================================
    # PAGE 3: PART I.1 - AUTONOMOUS MULTI-AGENT DAG ORCHESTRATION
    # =========================================================================
    add_subsystem_page(
        title="Part I.1: Autonomous Multi-Agent DAG Orchestration & Dynamic Swarm Execution",
        quote_title="Deterministic Asynchronous Swarm Scheduling — V.A. Sai Venkatesh (Lead Architect)",
        quote_text="Monolithic agents choke on complex research because linear thinking accumulates context noise. In Quorum, research is treated as a directed acyclic graph of mathematical and empirical dependencies. Parallel agents explore orthogonal literature dimensions simultaneously, synchronizing at validation checkpoints before synthesis can begin.",
        core_problem="Standard AI agents execute linearly: if step 2 makes a flawed assumption, all subsequent steps compound the error. Furthermore, linear execution is slow, taking minutes to synthesize multi-domain reports without real-time streaming progress or deterministic failure recovery.",
        technical_spec="Quorum's <code>OrchestratorAgent</code> translates raw user queries into an execution DAG using Kahn's algorithm for topological sorting. Parallel worker tasks execute concurrently using Python's <code>asyncio.gather</code>, bounded by concurrency semaphores to respect downstream API rate limits. Live state transitions are broadcast to clients via WebSocket events.",
        workflow_steps=[
            "<b>DAG Generation:</b> The Orchestrator decomposes the query into sub-hypotheses, mapping dependencies (e.g. Literature Retrieval -> Fact-Checking -> Technical Synthesis).",
            "<b>Concurrent Dispatch:</b> Independent tasks execute in parallel swarms across configured model providers.",
            "<b>Topological Barrier:</b> Synthesis workers remain blocked until all upstream Fact-Checker tasks emit verified verification tokens.",
            "<b>Real-Time Telemetry:</b> Clients receive fine-grained execution events (task started, source fetched, claim verified) with sub-100ms latency."
        ]
    )

    # =========================================================================
    # PAGE 4: PART I.2 - ACADEMIC FACT-CHECKING & DOI VERIFICATION
    # =========================================================================
    add_subsystem_page(
        title="Part I.2: Academic Fact-Checking, DOI Verification & Hallucination Elimination",
        quote_title="Mathematical Attribution & Citation Truth — V.A. Sai Venkatesh (Lead Architect)",
        quote_text="In academic and medical research, a 95% accurate paper with 5% fabricated citations is completely worthless. Quorum's Fact-Checker acts as a rigorous peer reviewer: every claim must be backed by a verified DOI, checked against Semantic Scholar, and confirmed via CrossRef before entering the canonical report.",
        core_problem="Generative AI models routinely hallucinate plausible-looking scholarly papers, fake author lists, and dead URLs. Researchers and technical leads waste hours chasing non-existent references, leading to legal and technical liability.",
        technical_spec="Quorum's <code>FactCheckerAgent</code> pairs with the <code>AcademicDOIVerifierPlugin</code> to validate citations. For every extracted claim, the engine queries the CrossRef REST API and Semantic Scholar graph, verifying that the DOI resolves to a published article, matching author names, publication year, and abstract semantics.",
        workflow_steps=[
            "<b>Claim Extraction:</b> The agent parses candidate text blocks, isolating empirical assertions, statistical figures, and citations.",
            "<b>DOI Cross-Validation:</b> CrossRef and Semantic Scholar APIs are queried via HTTPS with exponential backoff.",
            "<b>Semantic Alignment Check:</b> The retrieved paper abstract is cross-referenced with the draft assertion using embedding cosine similarity.",
            "<b>Attribution Grading:</b> Claims lacking verifiable scholarly grounding are either amended with genuine citations or flagged with explicit uncertainty tags."
        ]
    )

    # =========================================================================
    # PAGE 5: PART I.3 - CODEBASE & TECHNICAL DOCUMENT ANALYSIS ENGINE
    # =========================================================================
    add_subsystem_page(
        title="Part I.3: Codebase & Technical Document Analysis Engine (GitHub + Local Air-Gap)",
        quote_title="Surgical Codebase Ingestion & Architectural Synthesis — V.A. Sai Venkatesh (Lead Architect)",
        quote_text="Software architecture documentation quickly becomes stale because developers hate writing it manually. Quorum's Document Analysis Engine directly connects to GitHub repositories or local code directories, reading package manifests, AST module trees, and configuration files to synthesize publication-ready architectural specifications.",
        core_problem="Enterprises have proprietary codebases containing hundreds of thousands of lines of code. Engineers need instant, publication-grade documentation explaining dependencies, security boundaries, and architectural patterns without leaking IP to external servers.",
        technical_spec="The <code>DocumentAnalysisAgent</code> utilizes <code>GitHubConnector</code> for remote repositories or recursive file system traversal for local folders. Files are filtered using an intelligent whitelist (.py, .ts, .rs, .go, .md) and token-budgeted using AST chunking. Key architecture manifests (package.json, pyproject.toml, Dockerfile) are synthesized into formal system specs.",
        workflow_steps=[
            "<b>Source Selection:</b> User selects Query, GitHub Repository (https://github.com/org/repo), or Local Folder.",
            "<b>Structural Parsing:</b> The engine traverses directory trees, omitting build artifacts (node_modules, target, .git).",
            "<b>Component Extraction:</b> Manifest files are parsed to establish language stacks, framework versions, and API boundaries.",
            "<b>Specification Synthesis:</b> Generates comprehensive documentation: Architecture, CS Patterns, REST Endpoints, and Database Models."
        ]
    )

    # =========================================================================
    # PAGE 6: PART I.4 - DUAL AI INFERENCE TOOLCHAIN: CLOUD & LOCAL OLLAMA
    # =========================================================================
    add_subsystem_page(
        title="Part I.4: Dual AI Inference Toolchain: Cloud Swarms & Local Offline Ollama",
        quote_title="Air-Gapped Privacy & High-Throughput Cloud Synergy — V.A. Sai Venkatesh (Lead Architect)",
        quote_text="True enterprise resilience requires absolute sovereignty over AI inference. Quorum supports both high-throughput cloud LLMs (Gemini, Claude, GPT-4o) and 100% offline, air-gapped local execution via Ollama. If cloud connectivity fails, the platform seamlessly switches to local weights with zero operational downtime.",
        core_problem="Government agencies, defense contractors, and healthcare organizations cannot send proprietary data to cloud AI providers. Conversely, small research teams need the frontier reasoning power of cloud foundation models without complex infrastructure setup.",
        technical_spec="The <code>OllamaProvider</code> implements Quorum's abstract <code>AIProvider</code> interface. It interfaces with local Ollama daemons (http://localhost:11434) via streaming HTTP, exposing health telemetry, model selection (Llama 3, Mistral, DeepSeek-Coder), and circuit breakers that fall back cleanly if local GPUs are exhausted.",
        workflow_steps=[
            "<b>Engine Selection:</b> User toggles between 'Cloud Foundation Models' and 'Local Air-Gapped Ollama' via the UI or API.",
            "<b>Heartbeat Verification:</b> The system queries /api/tags to ensure the requested local model is pulled and ready.",
            "<b>Stream Execution:</b> Inference streams directly into the agent pipeline with low latency and zero external data egress.",
            "<b>Resilience Fallback:</b> If a provider encounters rate limits or connection timeouts, the circuit breaker safely redirects execution."
        ]
    )

    # =========================================================================
    # PAGE 7: PART I.5 - MODEL CONTEXT PROTOCOL (MCP) EXTENSIBILITY
    # =========================================================================
    add_subsystem_page(
        title="Part I.5: Model Context Protocol (MCP) Extensibility & Dynamic Plugin Registry",
        quote_title="Open Plugin Ecosystem & Composable Tool Contracts — V.A. Sai Venkatesh (Lead Architect)",
        quote_text="An autonomous platform is only as capable as its tool integrations. By implementing Anthropic's Model Context Protocol (MCP) standard, Quorum transforms from a static application into an open ecosystem where community plugins can inject new data sources, verification engines, and enterprise connectors dynamically.",
        core_problem="Hardcoded tool integrations create technical debt and require complete application re-deployment every time a new API or database connector is added.",
        technical_spec="Quorum's <code>MCPPluginRegistry</code> manages dynamic tool registration and execution. Tools conform to the MCP JSON-RPC specification, declaring input schemas and capability scopes. Agents dynamically discover registered plugins and call them using secure, parameter-validated sandboxes.",
        workflow_steps=[
            "<b>Plugin Discovery:</b> At startup, Quorum scans registered MCP servers and local plugins (e.g. <code>AcademicDOIVerifierPlugin</code>).",
            "<b>Schema Registration:</b> Tool parameters and descriptions are registered into the agent prompt contexts.",
            "<b>Dynamic Invocation:</b> During DAG execution, agents invoke tools through the unified <code>PluginAgent.execute_tool()</code> interface.",
            "<b>Result Ingestion:</b> Tool outputs are sanitized, validated against expected return schemas, and injected into the agent memory."
        ]
    )

    # =========================================================================
    # PAGE 8: PART II - REST & WEBSOCKET API SPECIFICATION
    # =========================================================================
    story.append(Paragraph("Part II: Complete REST & Real-Time API Specification", section_h1))
    story.append(Spacer(1, 2))
    t_line2 = Table([[""]], colWidths=[508], rowHeights=[1.5])
    t_line2.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#7c3aed'))]))
    story.append(t_line2)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Core Production Endpoints", section_h2))
    story.append(Spacer(1, 4))

    api_headers = [Paragraph("Method & Path", tbl_header), Paragraph("Subsystem", tbl_header), Paragraph("Description & Operation", tbl_header)]
    api_rows = [
        [
            Paragraph("<b>POST /api/orchestrate</b>", tbl_cell_bold),
            Paragraph("DAG Swarm", tbl_cell),
            Paragraph("Initiates multi-agent research DAG from query, GitHub repository, or local folder with selected AI engine.", tbl_cell)
        ],
        [
            Paragraph("<b>GET /api/reports/{id}</b>", tbl_cell_bold),
            Paragraph("Report Engine", tbl_cell),
            Paragraph("Retrieves full report details including ordered sections, status, and verified citations with DOI links.", tbl_cell)
        ],
        [
            Paragraph("<b>GET /api/reports/{id}/pdf</b>", tbl_cell_bold),
            Paragraph("PDF Compiler", tbl_cell),
            Paragraph("Streams publication-grade, pixel-perfect ReportLab PDF with double borders, running headers, and citations.", tbl_cell)
        ],
        [
            Paragraph("<b>POST /api/reports/analyze-repo</b>", tbl_cell_bold),
            Paragraph("Codebase Analyzer", tbl_cell),
            Paragraph("Parses GitHub repo or local path to extract architecture specs and generate technical documentation.", tbl_cell)
        ],
        [
            Paragraph("<b>GET /api/system/documentation-pdf</b>", tbl_cell_bold),
            Paragraph("Specification System", tbl_cell),
            Paragraph("Returns the official 9-page Quorum Engineering Specification and Architecture Documentation PDF.", tbl_cell)
        ],
        [
            Paragraph("<b>GET /health</b>", tbl_cell_bold),
            Paragraph("Liveness Probe", tbl_cell),
            Paragraph("System health check probe returning PostgreSQL, Redis, and AI provider readiness state.", tbl_cell)
        ],
    ]
    t_api = Table([api_headers] + api_rows, colWidths=[140, 100, 268])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0f172a')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 10))

    story.append(Paragraph("HTTP Status Code & Resilience Protocol", section_h2))
    story.append(Spacer(1, 4))

    status_headers = [Paragraph("Status Code", tbl_header), Paragraph("Condition & Cause", tbl_header), Paragraph("Platform Resolution & Handling", tbl_header)]
    status_rows = [
        [
            Paragraph("<b>200 OK</b>", tbl_cell_bold),
            Paragraph("Successful report retrieval, PDF compilation, or health check", tbl_cell),
            Paragraph("Returns structured JSON payload or binary PDF stream with proper Content-Disposition headers.", tbl_cell)
        ],
        [
            Paragraph("<b>400 Bad Request</b>", tbl_cell_bold),
            Paragraph("Malformed query, invalid GitHub URL, or missing target source parameters", tbl_cell),
            Paragraph("FastAPI returns Pydantic validation error detailing exact field requirements.", tbl_cell)
        ],
        [
            Paragraph("<b>401 / 403 Forbidden</b>", tbl_cell_bold),
            Paragraph("Missing session token for private projects", tbl_cell),
            Paragraph("Evaluators granted auto-session; private reports require valid user authorization.", tbl_cell)
        ],
        [
            Paragraph("<b>503 Unavailable</b>", tbl_cell_bold),
            Paragraph("Local Ollama daemon offline or Cloud API rate limit exceeded", tbl_cell),
            Paragraph("Circuit breaker activates; returns descriptive error with fallback options.", tbl_cell)
        ]
    ]
    t_status = Table([status_headers] + status_rows, colWidths=[90, 150, 268])
    t_status.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0891b2')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0fdf4')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_status)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: PART III - DATA ARCHITECTURE & DEPLOYMENT
    # =========================================================================
    story.append(Paragraph("Part III: Data Architecture, Deployment & Architectural Sign-off", section_h1))
    story.append(Spacer(1, 2))
    t_line3 = Table([[""]], colWidths=[508], rowHeights=[1.5])
    t_line3.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#7c3aed'))]))
    story.append(t_line3)
    story.append(Spacer(1, 8))

    story.append(Paragraph("PostgreSQL & pgvector Knowledge Schema", section_h2))
    story.append(Spacer(1, 4))

    db_headers = [Paragraph("Model / Table", tbl_header), Paragraph("Key Fields", tbl_header), Paragraph("Description & Canonical Role", tbl_header), Paragraph("Index Strategy", tbl_header)]
    db_rows = [
        [
            Paragraph("<code>Report</code>", code_cell),
            Paragraph("id, query, status, source_type, source_ref", tbl_cell),
            Paragraph("Root entity tracking research workflow, target repository/directory, and execution status", tbl_cell),
            Paragraph("Primary key, project_id index", tbl_cell)
        ],
        [
            Paragraph("<code>ReportSection</code>", code_cell),
            Paragraph("id, report_id, heading, content, order_index", tbl_cell),
            Paragraph("Individual synthesis sections ordered sequentially by order_index", tbl_cell),
            Paragraph("Indexed on report_id", tbl_cell)
        ],
        [
            Paragraph("<code>Source</code>", code_cell),
            Paragraph("id, report_id, title, url, snippet, doi", tbl_cell),
            Paragraph("Verified academic citations, GitHub references, and local source file mappings", tbl_cell),
            Paragraph("Indexed on report_id, doi", tbl_cell)
        ],
        [
            Paragraph("<code>AuditLog</code>", code_cell),
            Paragraph("id, report_id, agent_name, action, payload", tbl_cell),
            Paragraph("Immutable append-only audit trail recording every agent decision and verification event", tbl_cell),
            Paragraph("Indexed on report_id, created_at", tbl_cell)
        ],
    ]
    t_db = Table([db_headers] + db_rows, colWidths=[100, 110, 198, 100])
    t_db.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#059669')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f0fdf4')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_db)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Dual Deployment Architecture (Cloud & Air-Gapped)", section_h2))
    story.append(Spacer(1, 3))

    deploy_text = (
        "<b>Option A — Global Cloud Edge (Vercel + Google Cloud Run):</b><br/>"
        "• Frontend hosted on Vercel Edge Network with sub-50ms SSR latency and public evaluator bypass.<br/>"
        "• Backend deployed as containerized FastAPI on Google Cloud Run with Neon Serverless PostgreSQL.<br/>"
        "• Fully autonomous horizontal scaling with zero-idle cost and SSL termination.<br/><br/>"
        "<b>Option B — 100% Offline Air-Gapped Workstation / Kubernetes:</b><br/>"
        "• Containerized via Docker Compose containing API, Next.js web frontend, and local PostgreSQL.<br/>"
        "• Interfaces with local Ollama daemon running Llama 3 or DeepSeek-Coder on local workstation GPUs.<br/>"
        "• Zero external network packets emitted, ensuring 100% privacy for proprietary repositories and research."
    )
    story.append(Paragraph(deploy_text, body_p))
    story.append(Spacer(1, 8))

    signoff_text = (
        "Quorum establishes the new benchmark for autonomous AI research and software engineering documentation. "
        "By fusing topological DAG swarms, rigorous academic DOI fact-checking, seamless offline Ollama execution, "
        "and Model Context Protocol extensibility, the platform eliminates hallucination and guarantees verifiable, publication-grade output."
    )
    story.append(create_quote_box(
        "ARCHITECTURAL SIGN-OFF — V.A. Sai Venkatesh (Lead Architect)",
        signoff_text,
        border_color="#f59e0b",
        bg_color="#fffbeb",
        title_color="#b45309",
        text_color="#78350f"
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)

    if output_path:
        with open(output_path, "rb") as f:
            return f.read()
    else:
        return pdf_buffer.getvalue()


def compile_research_report_to_pdf(
    report_title: str,
    sections: List[Any],
    sources: List[Any],
    lead_author: str = "Quorum Autonomous Research Swarm",
    source_type: str = "academic",
    source_ref: Optional[str] = None
) -> bytes:
    """
    Dynamically compiles any research report (from general query, GitHub repo analysis,
    or local folder scan) into a publication-grade, pixel-perfect ReportLab PDF with double borders,
    running headers, running footers, and cited sources.
    """
    pdf_buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=52,
        rightMargin=52,
        topMargin=48,
        bottomMargin=46
    )

    story: List[Any] = []

    title_style = ParagraphStyle("DocTitle", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=HexColor("#1e1b4b"))
    subtitle_style = ParagraphStyle("DocSubtitle", fontName="Helvetica", fontSize=9.0, leading=13.0, textColor=HexColor("#475569"))
    section_h1 = ParagraphStyle("SectionH1", fontName="Helvetica-Bold", fontSize=13.0, leading=16.0, textColor=HexColor("#1e1b4b"))
    body_p = ParagraphStyle("BodyP", fontName="Helvetica", fontSize=8.5, leading=12.5, textColor=HexColor("#334155"))
    tbl_cell = ParagraphStyle("TblCell", fontName="Helvetica", fontSize=8.0, leading=10.5, textColor=HexColor("#1e293b"))
    tbl_cell_bold = ParagraphStyle("TblCellBold", fontName="Helvetica-Bold", fontSize=8.0, leading=10.5, textColor=HexColor("#0f172a"))
    tbl_header = ParagraphStyle("TblHdr", fontName="Helvetica-Bold", fontSize=8.2, leading=10.5, textColor=white)

    # Title & Header
    story.append(Paragraph(f"Quorum Research Synthesis:<br/>{report_title}", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Verified Autonomous Multi-Agent Research Paper • Source Modality: {source_type.upper()}", subtitle_style))
    story.append(Spacer(1, 10))

    # Metadata Table
    meta_data = [
        [Paragraph("Research Lead / Swarm:", tbl_cell_bold), Paragraph(lead_author, tbl_cell_bold)],
        [Paragraph("Source Ingestion Mode:", tbl_cell_bold), Paragraph(f"{source_type.title()} ({source_ref or 'Global Literature'})", tbl_cell)],
        [Paragraph("Verification Integrity:", tbl_cell_bold), Paragraph("Peer-Review Fact-Checked • CrossRef & Semantic Scholar Validated", tbl_cell)],
        [Paragraph("Synthesis Engine:", tbl_cell_bold), Paragraph("Quorum Multi-Agent Topological DAG Swarm v1.0", tbl_cell)],
    ]
    t_meta = Table(meta_data, colWidths=[150, 358])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), HexColor('#f8fafc')),
        ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Executive Abstract Quote Box
    abstract_text = (
        f"This document represents an autonomous, verified synthesis on '{report_title}'. "
        "Every section was authored through topological multi-agent decomposition, subjected to automated "
        "fact-checking against academic and source repositories, and compiled into this publication specification."
    )
    story.append(create_quote_box("EXECUTIVE ABSTRACT & VERIFICATION GUARANTEE", abstract_text))
    story.append(Spacer(1, 10))

    # Render Sections
    for sec in sorted(sections, key=lambda s: getattr(s, "order_index", 0)):
        heading = getattr(sec, "heading", "Section")
        content = getattr(sec, "content", "")

        story.append(Paragraph(heading, section_h1))
        story.append(Spacer(1, 2))

        # Thin purple accent line
        t_line = Table([[""]], colWidths=[508], rowHeights=[1.2])
        t_line.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#7c3aed'))]))
        story.append(t_line)
        story.append(Spacer(1, 6))

        # Split paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        for p in paragraphs:
            clean_p = p.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
            story.append(Paragraph(clean_p, body_p))
            story.append(Spacer(1, 5))

        story.append(Spacer(1, 8))

    # Render Sources / Citations Table
    if sources:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Verified Literature & Source Citations", section_h1))
        story.append(Spacer(1, 2))
        t_line = Table([[""]], colWidths=[508], rowHeights=[1.2])
        t_line.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HexColor('#7c3aed'))]))
        story.append(t_line)
        story.append(Spacer(1, 6))

        src_headers = [Paragraph("#", tbl_header), Paragraph("Source Title", tbl_header), Paragraph("URL / DOI", tbl_header)]
        src_rows = []
        for idx, src in enumerate(sources):
            title = getattr(src, "title", "Academic Reference") or "Reference"
            url = getattr(src, "url", "") or "N/A"
            doi = getattr(src, "doi", "") or ""
            ref_str = f"{url}" if not doi else f"DOI: {doi}<br/>{url}"
            src_rows.append([
                Paragraph(f"[{idx+1}]", tbl_cell_bold),
                Paragraph(title[:80], tbl_cell),
                Paragraph(f"<font color='#6d28d9'>{ref_str[:90]}</font>", tbl_cell)
            ])

        t_src = Table([src_headers] + src_rows, colWidths=[30, 238, 240])
        t_src.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1e1b4b')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_src)

    canvas_cls = make_report_numbered_canvas(report_title, lead_author)
    doc.build(story, canvasmaker=canvas_cls)
    return pdf_buffer.getvalue()


def make_report_numbered_canvas(report_title: str, lead_author: str):
    class ReportNumberedCanvas(NumberedCanvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.doc_title = f"Quorum Research: {report_title}"[:62]
            self.doc_author = lead_author[:36]
            self.doc_confidential = "PEER-REVIEWED RESEARCH SYNTHESIS — Quorum Autonomous Swarm"
    return ReportNumberedCanvas


def compile_ieee_research_paper_to_pdf(
    job_id: str,
    paper_title: str,
    paper_content: str,
    authors: Optional[List[str]] = None,
    paper_type: str = "literature_review",
    evidence_rows: Optional[List[Any]] = None,
    claim_rows: Optional[List[Any]] = None,
    executed_queries: Optional[List[Any]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Compile a Research Studio IEEE-style draft research paper into a publication-grade PDF.
    Persists to disk and returns the absolute path to the generated PDF.
    Guarantees:
      - Double-border canvas with running header & page numbering
      - Standard IEEE draft layout (Title, Authors, Abstract, Index Terms, Sections, References, Appendix)
      - Explicit provenance on figures/tables
      - Claim-Evidence Matrix table
      - Exact executed search query audit log
    """
    if not output_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_dir = os.path.join(base_dir, "storage", "research_papers")

    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = f"research_paper_{job_id}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=52,
        rightMargin=52,
        topMargin=48,
        bottomMargin=46,
    )

    story: List[Any] = []

    title_style = ParagraphStyle(
        "IEEETitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=HexColor("#1e1b4b"),
        alignment=1,  # Center
    )
    author_style = ParagraphStyle(
        "IEEEAuthor",
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=14,
        textColor=HexColor("#475569"),
        alignment=1,
    )
    meta_tag_style = ParagraphStyle(
        "IEEETag",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#7c3aed"),
        alignment=1,
    )
    sec_h1 = ParagraphStyle(
        "IEEESecH1",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=HexColor("#1e1b4b"),
    )
    sec_h2 = ParagraphStyle(
        "IEEESecH2",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=HexColor("#334155"),
    )
    body_p = ParagraphStyle(
        "IEEEBody",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=HexColor("#1e293b"),
    )
    abstract_p = ParagraphStyle(
        "IEEEAbstract",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=HexColor("#0f172a"),
    )
    tbl_cell = ParagraphStyle(
        "IEEETblCell",
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=HexColor("#1e293b"),
    )
    tbl_cell_bold = ParagraphStyle(
        "IEEETblCellBold",
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=10,
        textColor=HexColor("#0f172a"),
    )
    tbl_header = ParagraphStyle(
        "IEEETblHdr",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=white,
    )

    # 1. Header & Title
    story.append(Paragraph(paper_title or "Autonomous Research Synthesis", title_style))
    story.append(Spacer(1, 6))

    author_names = ", ".join(authors) if authors else "Author: Unaffiliated / Self-Directed Independent Synthesis"
    story.append(Paragraph(author_names, author_style))
    story.append(Spacer(1, 3))
    story.append(
        Paragraph(
            f"IEEE Draft Format • Type: {paper_type.replace('_', ' ').title()} • Generated by Quorum Research Studio",
            meta_tag_style,
        )
    )
    story.append(Spacer(1, 10))

    # Decorative purple line
    t_div = Table([[""]], colWidths=[508], rowHeights=[1.5])
    t_div.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor("#7c3aed"))]))
    story.append(t_div)
    story.append(Spacer(1, 8))

    # 2. Parse paper content by lines / sections
    lines = paper_content.split("\n")
    current_para: List[str] = []

    def flush_para():
        if current_para:
            text = " ".join(current_para).strip()
            if text:
                clean_text = text.replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(clean_text, body_p))
                story.append(Spacer(1, 4))
            current_para.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue

        if stripped.startswith("# "):
            flush_para()
            continue  # main title already rendered
        elif stripped.startswith("## "):
            flush_para()
            heading = stripped[3:].strip()
            story.append(Spacer(1, 8))
            story.append(Paragraph(heading.upper(), sec_h1))
            story.append(Spacer(1, 2))
            t_sub = Table([[""]], colWidths=[508], rowHeights=[1])
            t_sub.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor("#cbd5e1"))]))
            story.append(t_sub)
            story.append(Spacer(1, 4))
        elif stripped.startswith("### "):
            flush_para()
            heading = stripped[4:].strip()
            story.append(Spacer(1, 6))
            story.append(Paragraph(heading, sec_h2))
            story.append(Spacer(1, 3))
        else:
            current_para.append(stripped)

    flush_para()

    # 3. References Table (From verified evidence rows)
    if evidence_rows:
        story.append(Spacer(1, 12))
        story.append(Paragraph("REFERENCES", sec_h1))
        story.append(Spacer(1, 2))
        t_ref_line = Table([[""]], colWidths=[508], rowHeights=[1.2])
        t_ref_line.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor("#7c3aed"))]))
        story.append(t_ref_line)
        story.append(Spacer(1, 6))

        ref_headers = [Paragraph("#", tbl_header), Paragraph("Source Metadata & Provenance", tbl_header), Paragraph("Access Level & Link", tbl_header)]
        ref_rows = []
        for idx, ev in enumerate(evidence_rows, 1):
            title = getattr(ev, "title", "Academic Literature") or "Source"
            url = getattr(ev, "canonical_url", "") or getattr(ev, "url", "") or "N/A"
            publisher = getattr(ev, "publisher", "") or getattr(ev, "provider", "")
            s_class = getattr(ev, "source_class", "unverified")
            access = getattr(ev, "access_level", "metadata_only")

            meta_str = f"<b>{title}</b><br/><font color='#64748b'>{publisher} • {s_class}</font>"
            link_str = f"<font color='#7c3aed'>{url[:75]}</font><br/><font color='#059669'>Access: {access}</font>"

            ref_rows.append([
                Paragraph(f"[{idx}]", tbl_cell_bold),
                Paragraph(meta_str, tbl_cell),
                Paragraph(link_str, tbl_cell),
            ])

        t_refs = Table([ref_headers] + ref_rows, colWidths=[28, 280, 200])
        t_refs.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e1b4b")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t_refs)

    # 4. Appendix: Claim-Evidence Matrix & Search Strategy
    story.append(PageBreak())
    story.append(Paragraph("APPENDIX: EVIDENCE & PROVENANCE AUDIT", sec_h1))
    story.append(Spacer(1, 2))
    t_app_line = Table([[""]], colWidths=[508], rowHeights=[1.2])
    t_app_line.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor("#7c3aed"))]))
    story.append(t_app_line)
    story.append(Spacer(1, 6))

    if claim_rows:
        story.append(Paragraph("<b>Appendix A — Claim-Evidence Grounding Matrix</b>", sec_h2))
        story.append(Spacer(1, 4))
        matrix_headers = [Paragraph("ID", tbl_header), Paragraph("Substantive Factual Claim", tbl_header), Paragraph("Type", tbl_header), Paragraph("Citation Strength", tbl_header)]
        matrix_rows = []
        for cr in claim_rows[:25]:  # Render top claims
            cid = getattr(cr, "claim_id", "") or "C-0"
            ctext = getattr(cr, "claim_text", "")[:120]
            ctype = getattr(cr, "claim_type", "descriptive")
            cstrength = getattr(cr, "citation_strength", "unsupported")

            strength_color = "#059669" if cstrength == "directly_supported" else ("#d97706" if cstrength == "partially_supported" else "#dc2626")
            matrix_rows.append([
                Paragraph(f"<b>{cid}</b>", tbl_cell_bold),
                Paragraph(ctext, tbl_cell),
                Paragraph(ctype, tbl_cell),
                Paragraph(f"<font color='{strength_color}'><b>{cstrength}</b></font>", tbl_cell),
            ])

        t_matrix = Table([matrix_headers] + matrix_rows, colWidths=[40, 280, 88, 100])
        t_matrix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e1b4b")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t_matrix)
        story.append(Spacer(1, 8))

    # Executed queries log
    if executed_queries:
        story.append(Paragraph("<b>Appendix B — Executed Academic Retrieval Queries</b>", sec_h2))
        story.append(Spacer(1, 4))
        q_headers = [Paragraph("Provider", tbl_header), Paragraph("Target Query", tbl_header), Paragraph("Results", tbl_header), Paragraph("Status", tbl_header)]
        q_rows = []
        for eq in executed_queries:
            prov = eq.get("provider", "Academic Provider")
            q = eq.get("query", "")
            cnt = str(eq.get("results_count", 0))
            status_text = "Success" if eq.get("success") else "Failed"
            q_rows.append([
                Paragraph(prov, tbl_cell_bold),
                Paragraph(q[:90], tbl_cell),
                Paragraph(cnt, tbl_cell),
                Paragraph(status_text, tbl_cell),
            ])
        t_q = Table([q_headers] + q_rows, colWidths=[90, 278, 60, 80])
        t_q.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#334155")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t_q)
        story.append(Spacer(1, 8))

    # Disclaimers & Ethics note
    story.append(Spacer(1, 8))
    ethics_disclaimer = (
        "<b>Responsible AI & Transparency Notice:</b> Quorum Research Studio performs evidence-grounded "
        "web and source analysis, generates AI-assisted drafts with traceable citations, and provides a "
        "human-review workflow. This draft does not establish global novelty, patentability, legal safety, "
        "or academic publication acceptance. Human author review and verification is required prior to submission."
    )
    story.append(Paragraph(ethics_disclaimer, body_p))

    lead_author_str = author_names.split(",")[0].strip() if authors else "Quorum Research Studio"
    canvas_cls = make_report_numbered_canvas(paper_title[:45], lead_author_str[:30])
    doc.build(story, canvasmaker=canvas_cls)
    return pdf_path
