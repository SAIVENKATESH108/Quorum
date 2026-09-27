import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

/**
 * Evidence library proxy. Sources are retrieved directly from the FastAPI backend
 * which aggregates verified citations from report sources and agent findings.
 * Fails closed without unscoped fallback.
 */
export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const endpoint = `/api/sources${query ? `?${query}` : ""}`;
  return proxyToBackend(request, endpoint);
}
