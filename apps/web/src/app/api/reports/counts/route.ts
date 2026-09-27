import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

/**
 * Proxy for GET /api/reports/counts.
 * Returns authoritative per-status-group counts scoped to caller visibility.
 */
export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/api/reports/counts");
}
