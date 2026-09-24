import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl } from "@/lib/backend-proxy";

export async function POST(request: NextRequest) {
  const apiUrl = backendApiUrl();
  if (!apiUrl) {
    return NextResponse.json(
      { error: "Backend API is unavailable or not configured. If running in production, please configure NEXT_PUBLIC_API_URL." },
      { status: 503 }
    );
  }

  try {
    const body = await request.text();
    const response = await fetch(`${apiUrl}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      cache: "no-store",
    });

    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: text || "Invalid response received from auth server" },
        { status: 502 }
      );
    }

    if (!response.ok) return NextResponse.json(data, { status: response.status });
    const result = NextResponse.json({ user: data.user }, { status: 201 });
    result.cookies.set("quorum_session", data.token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24,
    });
    return result;
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to connect to authentication server" },
      { status: 503 }
    );
  }
}
