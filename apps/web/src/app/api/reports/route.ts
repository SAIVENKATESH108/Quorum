import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const endpoint = `/api/reports${query ? `?${query}` : ""}`;
  return proxyToBackend(request, endpoint);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const projectId = body.project_id || body.projectId;
    if (!projectId) {
      return NextResponse.json(
        { error: "bad_request", detail: "projectId is required to create a report" },
        { status: 400 }
      );
    }

    const payload = {
      query: body.query?.trim() || "Autonomous Multi-Agent Investigation",
      source_type: body.source_type || body.sourceType || "query",
      source_ref: body.source_ref || body.sourceRef || null,
      provider_mode: body.provider_mode || body.providerMode || "cloud",
    };

    return proxyToBackend(request, `/api/projects/${projectId}/reports`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "bad_request", detail: (err as Error).message },
      { status: 400 }
    );
  }
}
