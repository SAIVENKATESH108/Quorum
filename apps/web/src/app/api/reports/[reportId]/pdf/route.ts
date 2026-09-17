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
  } catch (err) {
    console.warn(`[PDF Route] Could not reach backend for report ${reportId}:`, err);
  }

  // Fallback to pre-compiled Quorum System Documentation PDF from public
  try {
    const publicPdfPath = path.join(process.cwd(), "public", "Quorum_System_Documentation.pdf");
    if (fs.existsSync(publicPdfPath)) {
      const fileBuffer = fs.readFileSync(publicPdfPath);
      return new NextResponse(fileBuffer, {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": `attachment; filename="Quorum_System_Documentation.pdf"`,
        },
      });
    }
  } catch (fallbackErr) {
    console.error("[PDF Route] Fallback file read failed:", fallbackErr);
  }

  return NextResponse.json(
    { error: "PDF compilation not available", detail: "Could not generate or locate PDF for this report." },
    { status: 404 }
  );
}
