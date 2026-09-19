import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  const apiUrl = backendApiUrl();

  if (apiUrl) {
    try {
      const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
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

  const reports = serverStore.getReports(projectId);
  return NextResponse.json(reports);
}

export async function POST(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  const body = await request.text();
  const apiUrl = backendApiUrl();

  if (apiUrl) {
    try {
      const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
        method: "POST",
        headers: backendHeaders(request),
        body,
        cache: "no-store",
      });
      if (res.ok) {
        return NextResponse.json(await res.json(), { status: res.status });
      }
    } catch {
      // Fall through to the local store.
    }
  }

  try {
    const payload = JSON.parse(body);
    const report = serverStore.createReport({
      query: payload.query,
      projectId,
      sourceType: payload.source_type,
      sourceRef: payload.source_ref,
      providerMode: payload.provider_mode,
    });

    if (!report) {
      return NextResponse.json(
        {
          error: "Project not found",
          detail: `No research project exists for id ${projectId}.`,
        },
        { status: 404 },
      );
    }

    return NextResponse.json(
      {
        id: report.id,
        report_id: report.id,
        status: report.status,
        query: report.query,
        created_at: report.created_at,
      },
      { status: 201 },
    );
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "Failed to create report", detail: (err as Error).message },
      { status: 400 },
    );
  }
}
