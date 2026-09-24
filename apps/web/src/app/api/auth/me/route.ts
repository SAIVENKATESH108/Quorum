import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const headers = backendHeaders(request);
  if (!headers.authorization) {
    return NextResponse.json(null);
  }

  const apiUrl = backendApiUrl();
  if (!apiUrl) {
    const cookie = request.cookies.get("quorum_session")?.value;
    if (cookie) {
      try {
        const decoded = JSON.parse(Buffer.from(cookie, "base64").toString("utf-8"));
        if (decoded && decoded.email) {
          return NextResponse.json(decoded);
        }
      } catch {
        return NextResponse.json({
          id: "user-primary",
          email: "researcher@quorum.ai",
          name: "Quorum Researcher",
          role: "member",
        });
      }
    }
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
