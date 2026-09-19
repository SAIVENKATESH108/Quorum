import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";

/**
 * Evidence library proxy. Sources always come from the backend (which aggregates
 * verified citations from report sections and agent findings); an empty library
 * is returned honestly when the backend is unreachable.
 */
export async function GET(request: NextRequest) {
  const apiUrl = backendApiUrl();

  if (!apiUrl) {
    return NextResponse.json([]);
  }

  try {
    const query = request.nextUrl.searchParams.toString();
    const res = await fetch(`${apiUrl}/api/sources${query ? `?${query}` : ""}`, {
      headers: backendHeaders(request),
      cache: "no-store",
    });
    if (res.ok) {
      return NextResponse.json(await res.json());
    }
  } catch {
    // Fall through to the empty library response.
  }

  return NextResponse.json([]);
}
