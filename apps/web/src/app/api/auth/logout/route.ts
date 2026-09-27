import { NextRequest, NextResponse } from "next/server";

const getBackendUrl = () =>
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const backendUrl = getBackendUrl().replace(/\/$/, "");
  const sessionCookie = request.cookies.get("quorum_session")?.value;
  const authHeader = request.headers.get("authorization");

  const forwardHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (authHeader) forwardHeaders["authorization"] = authHeader;
  if (sessionCookie) forwardHeaders["cookie"] = `quorum_session=${sessionCookie}`;

  try {
    await fetch(`${backendUrl}/api/auth/logout`, {
      method: "POST",
      headers: forwardHeaders,
    });
  } catch {
    // Fail-safe: even if backend is unreachable, always clear client cookies
  }

  const response = NextResponse.json({ ok: true, success: true, message: "Logged out successfully" });
  response.cookies.set("quorum_session", "", { httpOnly: true, expires: new Date(0), path: "/" });
  response.cookies.set("quorum_guest_session", "", { httpOnly: true, expires: new Date(0), path: "/" });
  return response;
}
