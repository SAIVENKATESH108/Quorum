import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const sessionCookie = request.cookies.get("quorum_session")?.value;
  const authHeader = request.headers.get("authorization");

  if (!authHeader && !sessionCookie) {
    return NextResponse.json(null);
  }

  // If session cookie is a valid base64-encoded user object (e.g. guest judge session)
  if (sessionCookie) {
    try {
      const decoded = JSON.parse(Buffer.from(sessionCookie, "base64").toString("utf-8"));
      if (decoded && decoded.email) {
        return NextResponse.json(decoded);
      }
    } catch {
      // not base64 json, proceed to backend API
    }
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
      return NextResponse.json(JSON.parse(text));
    } catch {
      return NextResponse.json(null);
    }
  } catch {
    return NextResponse.json(null);
  }
}
