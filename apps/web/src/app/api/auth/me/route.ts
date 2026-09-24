import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  const headers = backendHeaders(request);
  if (!headers.authorization) {
    return NextResponse.json(null);
  }

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
