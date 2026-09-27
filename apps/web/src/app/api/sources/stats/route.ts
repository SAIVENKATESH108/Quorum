import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

/**
 * Proxy for GET /api/sources/stats.
 * Forwards category query param and user credentials to the FastAPI backend.
 */
export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.toString();
  const endpoint = `/api/sources/stats${query ? `?${query}` : ""}`;
  return proxyToBackend(request, endpoint);
}
