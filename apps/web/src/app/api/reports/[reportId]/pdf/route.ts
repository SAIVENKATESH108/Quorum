import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const { reportId } = params;
  const apiUrl = backendApiUrl();

  if (!apiUrl) {
    return NextResponse.json(
      {
        error: "service_unavailable",
        detail: "The Quorum backend API is not configured or reachable from this runtime.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }

  const isInline = request.nextUrl.searchParams.get("preview") === "true";

  try {
    const backendRes = await fetch(`${apiUrl}/api/reports/${reportId}/pdf`, {
      headers: { ...backendHeaders(request), Accept: "application/pdf" },
      cache: "no-store",
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
          "X-Quorum-Data-Source": "fastapi_backend",
        },
      });
    }

    const detailText = await backendRes.text();
    return NextResponse.json(
      {
        error: "Publication PDF unavailable",
        detail: detailText,
      },
      {
        status: backendRes.status,
        headers: { "X-Quorum-Data-Source": "fastapi_backend" },
      }
    );
  } catch (_err: unknown) {
    return NextResponse.json(

      {
        error: "service_unavailable",
        detail: "The Quorum backend API is temporarily unreachable. Please retry.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }
}
