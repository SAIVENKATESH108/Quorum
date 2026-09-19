import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";

export async function GET(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
        headers: {
          "Content-Type": "application/json",
          ...(request.headers.get("authorization")
            ? { authorization: request.headers.get("authorization")! }
            : {}),
          ...(request.headers.get("cookie")
            ? { cookie: request.headers.get("cookie")! }
            : {}),
        },
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

  const reports = serverStore.getReports(projectId);
  return NextResponse.json(reports);
}

export async function POST(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  const body = await request.text();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const res = await fetch(`${apiUrl}/api/projects/${projectId}/reports`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(request.headers.get("authorization")
            ? { authorization: request.headers.get("authorization")! }
            : {}),
          ...(request.headers.get("cookie")
            ? { cookie: request.headers.get("cookie")! }
            : {}),
        },
        body,
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
