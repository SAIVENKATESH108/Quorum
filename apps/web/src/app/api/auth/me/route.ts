import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const apiUrl = backendApiUrl();
  if (!apiUrl) return NextResponse.json({ error: "Auth service unavailable" }, { status: 503 });
  const response = await fetch(`${apiUrl}/api/auth/me`, {
    headers: backendHeaders(request),
    cache: "no-store",
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
