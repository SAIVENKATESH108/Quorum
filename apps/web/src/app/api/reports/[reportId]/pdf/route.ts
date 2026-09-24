import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";
import { generateReportPdf } from "@/lib/pdf-generator";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const { reportId } = params;
  const apiUrl = backendApiUrl();

  const isInline = request.nextUrl.searchParams.get("preview") === "true";

  // 1. If backend API is configured and reachable, attempt fetching from FastAPI
  if (apiUrl) {
    try {
      const backendRes = await fetch(`${apiUrl}/api/reports/${reportId}/pdf`, {
        headers: { ...backendHeaders(request), Accept: "application/pdf" },
      });

      if (backendRes.ok) {
        const pdfBuffer = await backendRes.arrayBuffer();
        const contentDisposition = isInline
          ? "inline"
          : backendRes.headers.get("content-disposition") ||
            `attachment; filename="quorum_research_${reportId.slice(0, 8)}.pdf"`;

        return new NextResponse(pdfBuffer, {
          status: 200,
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": contentDisposition,
          },
        });
      }

      return NextResponse.json(
        {
          error: "Publication PDF unavailable",
          detail: await backendRes.text(),
        },
        { status: backendRes.status },
      );
    } catch (err) {
      console.error(`[PDF Route] Backend unreachable for ${reportId}:`, err);
      return NextResponse.json(
        {
          error: "Publication PDF service unavailable",
          detail: "The Python report service could not be reached.",
        },
        { status: 503 },
      );
    }
  }

  // 2. Compile the PDF for a report the agent pipeline actually produced.
  const report = await serverStore.getReport(reportId);
  if (!report) {
    return NextResponse.json(
      {
        error: "Report not found",
        detail: `No research report exists for id ${reportId}.`,
      },
      { status: 404 }
    );
  }

  if (report.sections.length === 0 && report.sources.length === 0) {
    return NextResponse.json(
      {
        error: "Report content is not ready",
        detail: "The research pipeline has not published sections or sources yet.",
      },
      { status: 404 },
    );
  }

  try {
    const pdfBuffer = generateReportPdf({
      reportTitle: report.query,
      sections: report.sections,
      sources: report.sources,
      leadAuthor: "Quorum Autonomous Multi-Agent Swarm",
      sourceType: "academic",
    });

    const slug = report.query
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .slice(0, 30)
      .replace(/^_+|_+$/g, "");

    const filename = `quorum_research_${slug}_${reportId.slice(0, 8)}.pdf`;

    return new NextResponse(new Uint8Array(pdfBuffer), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": isInline
          ? "inline"
          : `attachment; filename="${filename}"`,
      },
    });
  } catch (err: unknown) {
    console.error(`[PDF Route] Failed to compile PDF for ${reportId}:`, err);
    return NextResponse.json(
      {
        error: "Report PDF compilation failed",
        detail: (err as Error).message,
      },
      { status: 500 }
    );
  }
}
