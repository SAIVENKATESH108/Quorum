import { NextRequest, NextResponse } from "next/server";

const GUEST_COOKIE_NAME = "quorum_guest_session";
const GUEST_SESSION_MAX_AGE = 60 * 60 * 24; // 24 hours

export async function GET(req: NextRequest) {
  return handleSessionCreation(req);
}

export async function POST(req: NextRequest) {
  return handleSessionCreation(req);
}

function handleSessionCreation(req: NextRequest) {
  const url = new URL(req.url);
  const redirectTo = url.searchParams.get("redirect") || "/projects";

  // Build redirect URL preserving host
  const targetUrl = new URL(redirectTo, req.url);

  const response = NextResponse.redirect(targetUrl, { status: 303 });

  // Set secure HTTP-only guest session cookie
  response.cookies.set({
    name: GUEST_COOKIE_NAME,
    value: `judge-${Date.now()}`,
    maxAge: GUEST_SESSION_MAX_AGE,
    path: "/",
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
  });

  return response;
}
