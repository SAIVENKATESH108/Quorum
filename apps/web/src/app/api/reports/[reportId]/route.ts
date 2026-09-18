import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";
import { getScholarlyReport } from "@/lib/sample-reports-data";

export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const { reportId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  // 1. If backend API is configured and reachable, attempt proxying
  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const backendRes = await fetch(`${apiUrl}/api/reports/${reportId}`, {
        headers: { "Content-Type": "application/json" },
      });
      if (backendRes.ok) {
        const data = await backendRes.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend not reached, fall through to serverStore
    }
  }

  // 2. Check serverStore for dynamic report
  const stored = serverStore.getReport(reportId);
  if (stored) {
    return NextResponse.json(stored);
  }

  // 3. Return rich, verified academic report findings
  const searchParamQuery = request.nextUrl?.searchParams?.get("query") || "";
  const report = getScholarlyReport(reportId, searchParamQuery);
  return NextResponse.json(report);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const { reportId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      await fetch(`${apiUrl}/api/reports/${reportId}`, {
        method: "DELETE",
      });
    } catch {
      // Fall through
    }
  }

  const deleted = serverStore.deleteReport(reportId);
  if (!deleted) {
    return NextResponse.json({ error: "Report not found" }, { status: 404 });
  }

  return new NextResponse(null, { status: 204 });
}
