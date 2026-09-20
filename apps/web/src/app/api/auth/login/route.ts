import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl } from "@/lib/backend-proxy";

export async function POST(request: NextRequest) {
  const apiUrl = backendApiUrl() || process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
  if (!apiUrl) return NextResponse.json({ error: "Auth service unavailable" }, { status: 503 });
  const response = await fetch(`${apiUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
    cache: "no-store",
  });
  const data = await response.json();
  if (!response.ok) return NextResponse.json(data, { status: response.status });
  const result = NextResponse.json({ user: data.user });
  result.cookies.set("quorum_session", data.token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24,
  });
  return result;
}
