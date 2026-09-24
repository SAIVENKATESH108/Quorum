import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl } from "@/lib/backend-proxy";

export async function POST(request: NextRequest) {
  const apiUrl = backendApiUrl();
  if (!apiUrl) {
    try {
      const raw = await request.text();
      const body = JSON.parse(raw);
      const email = (body.email || "researcher@quorum.ai").toLowerCase().trim();
      const name = (body.name || email.split("@")[0]).trim();
      const user = {
        id: crypto.randomUUID(),
        email,
        name,
        role: "member",
      };
      const token = Buffer.from(JSON.stringify(user)).toString("base64");
      const isSecure = request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
      const result = NextResponse.json({ user }, { status: 201 });
      result.cookies.set("quorum_session", token, {
        httpOnly: true,
        secure: isSecure,
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 24,
      });
      return result;
    } catch {
      return NextResponse.json({ error: "Invalid registration payload format" }, { status: 400 });
    }
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
        { status: 502 }
      );
    }

    if (!response.ok) return NextResponse.json(data, { status: response.status });
    const isSecure = request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
    const result = NextResponse.json({ user: data.user }, { status: 201 });
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
      { error: err instanceof Error ? err.message : "Failed to connect to authentication server" },
      { status: 503 }
    );
  }
}
