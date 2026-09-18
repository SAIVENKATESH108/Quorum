import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";
import { generateReportPdf } from "@/lib/pdf-generator";
import { getScholarlyReport } from "@/lib/sample-reports-data";

export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const { reportId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  // 1. If backend API is configured and reachable, attempt fetching from FastAPI
  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const backendRes = await fetch(`${apiUrl}/api/reports/${reportId}/pdf`, {
        headers: { Accept: "application/pdf" },
      });

      if (backendRes.ok) {
        const pdfBuffer = await backendRes.arrayBuffer();
        const contentDisposition =
          backendRes.headers.get("content-disposition") ||
          `attachment; filename="quorum_research_${reportId.slice(0, 8)}.pdf"`;

        return new NextResponse(pdfBuffer, {
          status: 200,
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": contentDisposition,
          },
        });
      }
    } catch (err) {
      console.warn(`[PDF Route] Backend unreachable for ${reportId}, compiling locally:`, err);
    }
  }

  // 2. Compile publication-grade ReportLab-matching PDF directly on Vercel
  try {
    const stored = serverStore.getReport(reportId);
    const queryParam = request.nextUrl?.searchParams?.get("query") || "";
    const report = stored || getScholarlyReport(reportId, queryParam);

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
        "Content-Disposition": `attachment; filename="${filename}"`,
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
