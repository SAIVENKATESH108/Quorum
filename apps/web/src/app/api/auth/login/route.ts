import crypto from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { backendApiUrl } from "@/lib/backend-proxy";
import { getDb } from "@/lib/neon-db";

function verifyPassword(password: string, encoded: string | null): boolean {
  if (!encoded) return false;
  try {
    const parts = encoded.split("$");
    if (parts.length !== 4) return false;
    const [algorithm, roundsStr, saltHex, digestHex] = parts;
    if (algorithm !== "pbkdf2_sha256") return false;
    const rounds = parseInt(roundsStr, 10);
    const salt = Buffer.from(saltHex, "hex");
    const derived = crypto.pbkdf2Sync(password, salt, rounds, 32, "sha256");
    return crypto.timingSafeEqual(derived, Buffer.from(digestHex, "hex"));
  } catch {
    return false;
  }
}

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

  // 1. Try FastAPI backend if reachable
  const apiUrl = backendApiUrl();
  if (apiUrl) {
    try {
      const response = await fetch(`${apiUrl}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: rawBody,
        cache: "no-store",
      });

      if (response.ok) {
        const data = await response.json();
        const isSecure =
          request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
        const result = NextResponse.json({ user: data.user, token: data.token });
        result.cookies.set("quorum_session", data.token, {
          httpOnly: true,
          secure: isSecure,
          sameSite: "lax",
          path: "/",
          maxAge: 60 * 60 * 24,
        });
        return result;
      }
    } catch {
      // Backend not reached, fall through to direct Neon verification
    }
  }

  // 2. Direct Neon PostgreSQL authentication (Vercel Serverless / Cloud mode)
  try {
    const sql = getDb();
    const rows = await sql`
      SELECT id, email, name, role, password_hash
      FROM public.users
      WHERE LOWER(email) = ${email}
      LIMIT 1;
    `;

    if (!rows || rows.length === 0) {
      return NextResponse.json(
        { error: "Invalid email or password", detail: "No registered account matches this email." },
        { status: 401 }
      );
    }

    const userRecord = rows[0];
    const isValid = verifyPassword(password, userRecord.password_hash);
    if (!isValid) {
      return NextResponse.json(
        { error: "Invalid email or password", detail: "Incorrect password entered." },
        { status: 401 }
      );
    }

    const user = {
      id: userRecord.id,
      email: userRecord.email,
      name: userRecord.name || userRecord.email.split("@")[0],
      role: userRecord.role || "member",
    };

    const token = Buffer.from(JSON.stringify(user)).toString("base64");
    const isSecure =
      request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
    const result = NextResponse.json({ user, token });
    result.cookies.set("quorum_session", token, {
      httpOnly: true,
      secure: isSecure,
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24,
    });

    return result;
  } catch (err: unknown) {
    console.error("[Login Route] Neon authentication error:", err);
    return NextResponse.json(
      { error: "Authentication service error", detail: (err as Error).message },
      { status: 500 }
    );
  }
}
