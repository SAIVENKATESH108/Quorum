import type { NextRequest } from "next/server";

/**
 * Base URL of the FastAPI backend when it is reachable from the Next.js runtime.
 *
 * Returns null for unset or localhost URLs, since a localhost backend is never
 * reachable from a deployed serverless/edge runtime.
 */
export function backendApiUrl(): string | null {
  const apiUrl = (
    process.env.FASTAPI_URL ||
    process.env.API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8000"
  ).replace(/\/$/, "");

  // When deployed to Vercel/cloud, an unconfigured localhost URL cannot be contacted.
  const isLocal = apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");
  const isCloud = Boolean(process.env.VERCEL || process.env.VERCEL_ENV);
  if (isCloud && isLocal) {
    return null;
  }

  return apiUrl;
}

/**
 * Headers forwarded to the FastAPI backend for a proxied request.
 *
 * The caller's credentials are forwarded so the backend can authenticate the
 * request and enforce ownership scoping exactly as it does end-to-end.
 */
export function backendHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const authorization = request.headers.get("authorization");
  const cookie = request.headers.get("cookie");
  const session = cookie?.match(/(?:^|;\s*)quorum_session=([^;]+)/)?.[1];
  if (authorization) headers.authorization = authorization;
  else if (session) headers.authorization = `Bearer ${decodeURIComponent(session)}`;
  if (cookie) headers.cookie = cookie;
  return headers;
}
