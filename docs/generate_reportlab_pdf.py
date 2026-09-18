"""
Quorum Complete Engineering Specification & System Documentation Generator
Uses ReportLab to produce a pixel-perfect, publication-grade 9-page PDF matching
the exact structure, double borders, typography, quote boxes, tables, and architectural specifications
of Quorum — Autonomous Multi-Agent AI Research & Verification Platform.
"""

import os
import sys

# Add apps/api to path so we can import pdf_generator
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_DIR)
API_DIR = os.path.join(REPO_ROOT, "apps", "api")
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from src.services.pdf_generator import build_quorum_system_documentation_pdf

DOCS_DIR = os.path.join(REPO_ROOT, "docs")
PUBLIC_DIR = os.path.join(REPO_ROOT, "apps", "web", "public")

PDF_OUT_DOCS = os.path.join(DOCS_DIR, "Quorum_System_Documentation.pdf")
PDF_OUT_PUBLIC = os.path.join(PUBLIC_DIR, "Quorum_System_Documentation.pdf")


def main() -> None:
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    print("Building Quorum System Documentation via ReportLab...")
    pdf_bytes = build_quorum_system_documentation_pdf(
        output_path=PDF_OUT_DOCS,
        image_dir=PUBLIC_DIR,
    )

    with open(PDF_OUT_PUBLIC, "wb") as f:
        f.write(pdf_bytes)

    size_kb = len(pdf_bytes) / 1024
    print("Generated 9-Page System Documentation PDF:")
    print(f"  -> Docs output:   {PDF_OUT_DOCS} ({size_kb:.1f} KB)")
    print(f"  -> Public output: {PDF_OUT_PUBLIC} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
