import { NextRequest, NextResponse } from "next/server";

const DEFAULT_PROJECTS = [
  {
    id: "a9d930d2-03dd-431e-9390-246925165e9a",
    user_id: "judge-user",
    title: "Consensus & Byzantine Fault Tolerance",
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "b4f8812c-91aa-4231-897c-31a198c2514d",
    user_id: "judge-user",
    title: "Distributed LLM Agent Orchestration",
    created_at: new Date(Date.now() - 43200000).toISOString(),
  },
];

export async function GET() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

  if (apiUrl && !apiUrl.includes("localhost")) {
    try {
      const res = await fetch(`${apiUrl}/api/projects`, {
        headers: { "Content-Type": "application/json" },
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // Fall through to default projects
    }
  }

  return NextResponse.json(DEFAULT_PROJECTS);
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const newProject = {
      id: crypto.randomUUID(),
      user_id: "current-user",
      title: body.title || "Autonomous Research Project",
      created_at: new Date().toISOString(),
    };
    return NextResponse.json(newProject, { status: 201 });
  } catch (err: unknown) {
    return NextResponse.json(
      { error: "Failed to create project", detail: (err as Error).message },
      { status: 400 }
    );
  }
}
