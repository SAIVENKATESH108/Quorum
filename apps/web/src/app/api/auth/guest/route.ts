import { NextRequest, NextResponse } from "next/server";

const GUEST_USER = {
  id: "00000000-0000-4000-8000-000000000001",
  email: "judge@quorum.ai",
  name: "Guest Judge",
  role: "member" as const,
};

export async function GET(request: NextRequest) {
  return handleGuestSession(request);
}

export async function POST(request: NextRequest) {
  return handleGuestSession(request);
}

function handleGuestSession(request: NextRequest) {
  const url = new URL(request.url);
  const redirectTo = url.searchParams.get("redirect") || "/projects";
  const token = Buffer.from(JSON.stringify(GUEST_USER)).toString("base64");

  const acceptsJson =
    request.headers.get("accept")?.includes("application/json") ||
    request.headers.get("content-type")?.includes("application/json");

  // If request is from fetch expecting JSON
  if (request.method === "POST" && acceptsJson) {
    const response = NextResponse.json({
      user: GUEST_USER,
      token,
      redirect: redirectTo,
    });
    setSessionCookies(response, token, request);
    return response;
  }

  // Otherwise perform 303 See Other redirect
  const targetUrl = new URL(redirectTo, request.url);
  const response = NextResponse.redirect(targetUrl, { status: 303 });
  setSessionCookies(response, token, request);
  return response;
}

function setSessionCookies(response: NextResponse, token: string, request: NextRequest) {
  const isSecure =
    request.nextUrl.protocol === "https:" ||
    request.headers.get("x-forwarded-proto") === "https";

  response.cookies.set("quorum_session", token, {
    httpOnly: true,
    secure: isSecure,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24, // 24 hours
  });
  response.cookies.set("quorum_guest_session", `judge-${Date.now()}`, {
    httpOnly: true,
    secure: isSecure,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24,
  });
}
