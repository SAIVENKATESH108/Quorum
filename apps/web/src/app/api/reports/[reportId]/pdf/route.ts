import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const { reportId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

  try {
    // Attempt fetching generated PDF directly from FastAPI backend
    const backendRes = await fetch(`${apiUrl}/api/reports/${reportId}/pdf`, {
      headers: {
        Accept: "application/pdf",
      },
    });

    if (backendRes.ok) {
      const pdfBuffer = await backendRes.arrayBuffer();
      return new NextResponse(pdfBuffer, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": `attachment; filename="quorum_report_${reportId.slice(0, 8)}.pdf"`,
        },
      });
    }
  } catch (err: unknown) {
    console.warn(`[PDF Route] Could not reach backend for report ${reportId}:`, err);
    return NextResponse.json(
      {
        error: "PDF service unavailable",
        detail: `Could not connect to Quorum backend PDF service: ${(err as Error).message}`,
      },
      { status: 503 }
    );
  }

  return NextResponse.json(
    {
      error: "Report PDF compilation unavailable",
      detail: `Could not compile or retrieve publication PDF for report ${reportId}. Please ensure the report exists and has completed synthesis.`,
    },
    { status: 404 }
  );
}
