import { NextRequest, NextResponse } from "next/server";
import { SCHOLARLY_REPORTS } from "@/lib/sample-reports-data";

export async function GET() {
  const reports = Object.values(SCHOLARLY_REPORTS).map((r) => ({
    id: r.id,
    project_id: r.project_id,
    status: r.status,
    query: r.query,
    created_at: r.created_at,
    completed_at: r.completed_at,
    error_message: r.error_message,
  }));

  return NextResponse.json(reports);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = body.query?.trim() || "Autonomous Multi-Agent Investigation";
    const reportId = crypto.randomUUID();

    return NextResponse.json({
      id: reportId,
      report_id: reportId,
      status: "complete",
      query: query,
      created_at: new Date().toISOString(),
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "Invalid request payload", detail: (err as Error).message },
      { status: 400 }
    );
  }
}
