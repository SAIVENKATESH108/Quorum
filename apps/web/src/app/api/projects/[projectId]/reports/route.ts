import { NextRequest, NextResponse } from "next/server";
import { SCHOLARLY_REPORTS } from "@/lib/sample-reports-data";

export async function GET(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through
    }
  }

  const reports = Object.values(SCHOLARLY_REPORTS)
    .filter((r) => r.project_id === projectId || !projectId)
    .map((r) => ({
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
