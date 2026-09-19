import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const apiUrl = backendApiUrl();

  if (apiUrl) {
    try {
      // Authenticated, user-scoped data must never be served from the fetch cache.
      const res = await fetch(`${apiUrl}/api/projects`, {
        headers: backendHeaders(request),
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through to serverStore
    }
  }

  const projects = serverStore.getProjects();
  return NextResponse.json(projects);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const title = body.title?.trim() || "Autonomous Research Domain";
    const apiUrl = backendApiUrl();

    if (apiUrl) {
      try {
        const res = await fetch(`${apiUrl}/api/projects`, {
          method: "POST",
          headers: backendHeaders(request),
          body: JSON.stringify({ title }),
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

    const newProject = serverStore.createProject(title);
    return NextResponse.json(newProject, { status: 201 });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "Failed to create project", detail: (err as Error).message },
      { status: 400 }
    );
  }
}
