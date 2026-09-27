import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const sessionCookie = request.cookies.get("quorum_session")?.value;
  const authHeader = request.headers.get("authorization");

  if (!authHeader && !sessionCookie) {
    return NextResponse.json(null);
  }

  const headers = backendHeaders(request);
  const apiUrl = backendApiUrl();
  if (!apiUrl) {
    return NextResponse.json(null);
  }

  try {
    const response = await fetch(`${apiUrl}/api/auth/me`, {
      headers,
      cache: "no-store",
    });
    if (!response.ok) {
      return NextResponse.json(null);
    }
    const text = await response.text();
    try {
      const data = JSON.parse(text);
      if (data && data.role === "guest") {
        data.email = "";
        data.name = "Guest Judge";
      }
      return NextResponse.json(data);
    } catch {
      return NextResponse.json(null);
    }
  } catch {
    return NextResponse.json(null);
  }
}
