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
      const res = await fetch(`${apiUrl}/api/projects/${projectId}`, {
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

  const project = await serverStore.getProject(projectId);
  if (!project) {
    return NextResponse.json({ error: "Project not found" }, { status: 404 });
  }

  return NextResponse.json(project);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  try {
    const body = await request.json();
    const title = body.title?.trim();
    if (!title) {
      return NextResponse.json({ error: "Title is required" }, { status: 400 });
    }

    const apiUrl = backendApiUrl();
    if (apiUrl) {
      try {
        const res = await fetch(`${apiUrl}/api/projects/${projectId}`, {
          method: "PATCH",
          headers: backendHeaders(request),
          body: JSON.stringify({ title }),
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

    const updated = await serverStore.updateProject(projectId, title);
    if (!updated) {
      return NextResponse.json({ error: "Project not found" }, { status: 404 });
    }

    return NextResponse.json(updated);
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "Failed to update project", detail: (err as Error).message },
      { status: 400 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const { projectId } = params;
  const apiUrl = backendApiUrl();

  if (apiUrl) {
    try {
      await fetch(`${apiUrl}/api/projects/${projectId}`, {
        method: "DELETE",
        headers: backendHeaders(request),
        cache: "no-store",
      });
    } catch {
      // Fall through
    }
  }

  const deleted = await serverStore.deleteProject(projectId);
  if (!deleted) {
    // DELETE is idempotent: the requested project is already absent.
    return new NextResponse(null, { status: 204 });
  }

  return new NextResponse(null, { status: 204 });
}
