import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl } from "@/lib/backend-proxy";

export async function POST(request: NextRequest) {
  let bodyJson: { email?: string; password?: string } = {};
  let rawBody = "";
  try {
    rawBody = await request.text();
    bodyJson = JSON.parse(rawBody);
  } catch {
    return NextResponse.json({ error: "Invalid login credentials format" }, { status: 400 });
  }

  const email = (bodyJson.email || "").toLowerCase().trim();
  const password = bodyJson.password || "";

  if (!email || !password) {
    return NextResponse.json({ error: "Email and password are required" }, { status: 400 });
  }

  const apiUrl = backendApiUrl();
  if (!apiUrl) {
    return NextResponse.json(
      {
        error: "service_unavailable",
        detail: "The Quorum backend authentication service is not configured or reachable.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }

  try {
    const response = await fetch(`${apiUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: rawBody,
      cache: "no-store",
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      return NextResponse.json(
        data || { error: "Authentication failed", detail: "Invalid credentials" },
        {
          status: response.status,
          headers: { "X-Quorum-Data-Source": "fastapi_backend" },
        }
      );
    }

    const isSecure =
      request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
    const result = NextResponse.json(
      { user: data.user, token: data.token },
      {
        status: 200,
        headers: { "X-Quorum-Data-Source": "fastapi_backend" },
      }
    );

    result.cookies.set("quorum_session", data.token, {
      httpOnly: true,
      secure: isSecure,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24,
    });

    return result;
  } catch (_err: unknown) {
    return NextResponse.json(

      {
        error: "service_unavailable",
        detail: "The Quorum backend authentication service is temporarily unreachable. Please retry.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }
}

