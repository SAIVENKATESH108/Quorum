import { NextRequest, NextResponse } from "next/server";

const getBackendUrl = () =>
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  return handleGuestSession(request);
}

export async function GET(request: NextRequest) {
  return handleGuestSession(request);
}

async function handleGuestSession(request: NextRequest) {
  const backendUrl = getBackendUrl().replace(/\/$/, "");

  const forwardHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const ua = request.headers.get("user-agent");
  if (ua) forwardHeaders["user-agent"] = ua;
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) forwardHeaders["x-forwarded-for"] = forwardedFor;

  try {
    const res = await fetch(`${backendUrl}/api/auth/guest`, {
      method: "POST",
      headers: forwardHeaders,
    });

    if (!res.ok) {
      const errText = await res.text();
      return NextResponse.json(
        { error: "Failed to initialize guest judge session", detail: errText },
        { status: res.status }
      );
    }

    const data = await res.json();
    const setCookieHeader = res.headers.get("set-cookie");
    const sessionCookieMatch = setCookieHeader?.match(/(?:^|;\s*)quorum_session=([^;]+)/);
    const sessionCookie = sessionCookieMatch ? sessionCookieMatch[1] : null;

    const url = new URL(request.url);
    const redirectTo = url.searchParams.get("redirect") || "/projects";
    const acceptsJson =
      request.headers.get("accept")?.includes("application/json") ||
      request.headers.get("content-type")?.includes("application/json");

    const isSecure =
      request.nextUrl.protocol === "https:" ||
      request.headers.get("x-forwarded-proto") === "https" ||
      process.env.NODE_ENV === "production";

    // Safe session metadata only (no raw tokens/JWTs in JSON)
    const safeBody = {
      success: true,
      session_type: "guest",
      role: "guest",
      expires_at: data.expires_at,
      redirect: redirectTo,
    };

    const response =
      request.method === "POST" && acceptsJson
        ? NextResponse.json(safeBody)
        : NextResponse.redirect(new URL(redirectTo, request.url), { status: 303 });

    if (sessionCookie) {
      response.cookies.set("quorum_session", sessionCookie, {
        httpOnly: true,
        secure: isSecure,
        sameSite: "lax",
        path: "/",
        maxAge: 4 * 3600,
      });
    }

    return response;
  } catch (err: any) {
    return NextResponse.json(
      { error: "Backend service unreachable", detail: err?.message },
      { status: 503 }
    );
  }
}
