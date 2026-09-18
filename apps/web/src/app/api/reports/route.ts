import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const res = await fetch(`${apiUrl}/api/reports`, {
        headers: { "Content-Type": "application/json" },
        next: { revalidate: 15 },
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through
    }
  }

  const reports = serverStore.getReports();
  return NextResponse.json(reports);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = body.query?.trim() || "Autonomous Multi-Agent Investigation";
    const projectId = body.project_id || body.projectId;
    const sourceType = body.source_type || body.sourceType || "query";
    const sourceRef = body.source_ref || body.sourceRef;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
    if (apiUrl && !apiUrl.includes("localhost") && projectId) {
      try {
        const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            source_type: sourceType,
            source_ref: sourceRef,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          return NextResponse.json(data, { status: 201 });
        }
      } catch {
        // Fall through
      }
    }

    const created = serverStore.createReport({
      query,
      projectId,
      sourceType,
      sourceRef,
    });

    return NextResponse.json(
      {
        id: created.id,
        report_id: created.id,
        status: created.status,
        query: created.query,
        created_at: created.created_at,
      },
      { status: 201 }
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "Invalid request payload", detail: (err as Error).message },
      { status: 400 }
    );
  }
}
