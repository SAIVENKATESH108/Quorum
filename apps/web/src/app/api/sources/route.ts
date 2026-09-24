import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl, backendHeaders } from "@/lib/backend-proxy";
import { serverStore } from "@/lib/server-store";

/**
 * Evidence library proxy. Sources are retrieved from the backend (which aggregates
 * verified citations from report sources and agent findings) with fallback to
 * serverStore.
 */
export async function GET(request: NextRequest) {
  const category = request.nextUrl.searchParams.get("category") || undefined;
  const apiUrl = backendApiUrl();

  if (apiUrl) {
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
      // Fall through to server store fallback
    }
  }

  return NextResponse.json(serverStore.getSources(category));
}
