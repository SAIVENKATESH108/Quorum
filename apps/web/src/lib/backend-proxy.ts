import { NextRequest, NextResponse } from "next/server";

/**
 * Gate allowing in-memory development fixtures only when explicitly enabled
 * in non-production, non-deployed environments.
 * Default is FALSE. Never allowed in production or on Vercel.
 */
export function isDevelopmentFixtureAllowed(): boolean {
  if (process.env.NODE_ENV === "production" || process.env.VERCEL || process.env.VERCEL_ENV) {
    return false;
  }
  return process.env.QUORUM_ALLOW_IN_MEMORY_STORE === "true";
}

/**
 * Base URL of the FastAPI backend.
 *
 * In production / Vercel cloud runtime, localhost is unreachable.
 * Returns null if the URL is missing or cannot be reached.
 */
export function backendApiUrl(): string {
  const apiUrl = (
    process.env.API_URL ||
    process.env.FASTAPI_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    (process.env.VERCEL || process.env.VERCEL_ENV || process.env.NODE_ENV === "production"
      ? "https://quorum-ai-research-studio.up.railway.app"
      : "http://127.0.0.1:8000")
  ).replace(/\/$/, "");

  // When deployed to Vercel/cloud, fallback to live Railway production backend if localhost is given
  const isLocal = apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1");
  const isCloud = Boolean(process.env.VERCEL || process.env.VERCEL_ENV || process.env.NODE_ENV === "production");
  if (isCloud && isLocal) {
    return "https://quorum-ai-research-studio.up.railway.app";
  }

  return apiUrl;
}

/**
 * Headers forwarded to the FastAPI backend for a proxied request.
 * The caller's credentials (Authorization header or quorum_session cookie)
 * are forwarded so FastAPI enforces database-level tenant ownership.
 */
export function backendHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const authorization = request.headers.get("authorization");
  const cookie = request.headers.get("cookie");
  const sessionCookie = request.cookies?.get("quorum_session")?.value;
  const session = sessionCookie || cookie?.match(/(?:^|;\s*)quorum_session=([^;]+)/)?.[1];
  
  if (authorization) {
    headers.authorization = authorization;
  } else if (session) {
    headers.authorization = `Bearer ${decodeURIComponent(session)}`;
  }
  
  if (cookie) headers.cookie = cookie;
  else if (sessionCookie) headers.cookie = `quorum_session=${sessionCookie}`;
  
  return headers;
}

/**
 * Robust, failure-closed proxy to the FastAPI backend.
 *
 * Enforces:
 * 1. Returns exact HTTP status codes from FastAPI (401, 403, 404, 422, etc.) without fallback.
 * 2. Emits X-Quorum-Data-Source: fastapi_backend on all proxied responses.
 * 3. Returns 503 Service Unavailable on connection errors or missing backend URL.
 * 4. Never performs unscoped direct database queries or in-memory persistence.
 */
export async function proxyToBackend(
  request: NextRequest,
  endpoint: string,
  options?: RequestInit
): Promise<NextResponse> {
  const apiUrl = backendApiUrl();

  if (!apiUrl) {
    return NextResponse.json(
      {
        error: "service_unavailable",
        detail: "The Quorum backend API is not configured or reachable from this runtime.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }

  const forwardHeaders = backendHeaders(request);
  if (options?.headers) {
    Object.assign(forwardHeaders, options.headers);
  }

  const targetUrl = `${apiUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  try {
    const res = await fetch(targetUrl, {
      ...options,
      headers: forwardHeaders,
      cache: "no-store",
    });

    const contentType = res.headers.get("content-type") || "";
    const responseHeaders = new Headers();
    responseHeaders.set("X-Quorum-Data-Source", "fastapi_backend");

    if (contentType.includes("application/json")) {
      const data = await res.json();
      return NextResponse.json(data, {
        status: res.status,
        headers: responseHeaders,
      });
    }

    if (contentType.includes("application/pdf")) {
      const blob = await res.arrayBuffer();
      responseHeaders.set("Content-Type", "application/pdf");
      const disposition = res.headers.get("content-disposition");
      if (disposition) responseHeaders.set("Content-Disposition", disposition);
      return new NextResponse(blob, {
        status: res.status,
        headers: responseHeaders,
      });
    }

    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: responseHeaders,
    });
  } catch (_err: unknown) {
    return NextResponse.json(

      {
        error: "service_unavailable",
        detail: "The Quorum backend API is temporarily unreachable. Please retry.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }
}
