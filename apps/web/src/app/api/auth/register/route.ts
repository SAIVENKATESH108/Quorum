import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl } from "@/lib/backend-proxy";

export async function POST(request: NextRequest) {
  const apiUrl = backendApiUrl();
  if (!apiUrl) {
    return NextResponse.json(
      {
        error: "service_unavailable",
        detail: "The Quorum backend registration service is not configured or reachable.",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }

  try {
    const body = await request.text();
    const response = await fetch(`${apiUrl}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      cache: "no-store",
    });

    const text = await response.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      return NextResponse.json(
        { error: text || "Invalid response received from auth server" },
        {
          status: 502,
          headers: { "X-Quorum-Data-Source": "fastapi_backend" },
        }
      );
    }

    if (!response.ok) {
      return NextResponse.json(data, {
        status: response.status,
        headers: { "X-Quorum-Data-Source": "fastapi_backend" },
      });
    }

    const isSecure = request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
    const result = NextResponse.json(
      { user: data.user },
      {
        status: 201,
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
  } catch (err) {
    return NextResponse.json(
      {
        error: "service_unavailable",
        detail: err instanceof Error ? err.message : "Failed to connect to authentication server",
      },
      {
        status: 503,
        headers: { "X-Quorum-Data-Source": "unavailable" },
      }
    );
  }
}

