import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const apiUrl = backendApiUrl();

  if (apiUrl) {
    try {
      // Authenticated, user-scoped data must never be served from the fetch cache.
      const res = await fetch(`${apiUrl}/api/reports`, {
        headers: backendHeaders(request),
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through
    }
  }

  const reports = await serverStore.getReports();
  return NextResponse.json(reports);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = body.query?.trim() || "Autonomous Multi-Agent Investigation";
    const projectId = body.project_id || body.projectId;
    const sourceType = body.source_type || body.sourceType || "query";
    const sourceRef = body.source_ref || body.sourceRef;
    const providerMode = body.provider_mode || body.providerMode || "cloud";

    const apiUrl = backendApiUrl();
    if (apiUrl && projectId) {
      try {
        const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
          method: "POST",
          headers: backendHeaders(request),
          body: JSON.stringify({
            query,
            source_type: sourceType,
            source_ref: sourceRef,
            provider_mode: providerMode,
          }),
          cache: "no-store",
        });
        if (res.ok) {
          const data = await res.json();
          return NextResponse.json(data, { status: 201 });
        }
      } catch {
        // Fall through
      }
    }

    const created = await serverStore.createReport({
      query,
      projectId,
      sourceType,
      sourceRef,
      providerMode,
    });

    if (!created) {
      return NextResponse.json(
        {
          error: "Project not found",
          detail: "A valid project_id is required to schedule a research report.",
        },
        { status: 404 }
      );
    }

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
