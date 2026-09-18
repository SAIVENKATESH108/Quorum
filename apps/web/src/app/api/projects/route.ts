import { NextRequest, NextResponse } from "next/server";
import { serverStore } from "@/lib/server-store";

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const res = await fetch(`${apiUrl}/api/projects`, {
        headers: { "Content-Type": "application/json" },
        next: { revalidate: 15 },
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
    const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

    if (apiUrl && !apiUrl.includes("localhost")) {
      try {
        const res = await fetch(`${apiUrl}/api/projects`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title }),
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
