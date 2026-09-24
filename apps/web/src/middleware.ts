import { NextRequest, NextResponse } from "next/server";

// All workspace and telemetry views are public in read-only mode so hackathon judges
// and evaluators can view projects, reports, evidence, agent mesh, and settings without hitting auth walls.
const isPublicPath = (pathname: string) =>
  pathname === "/" ||
  pathname.startsWith("/sign-in") ||
  pathname.startsWith("/sign-up") ||
  pathname.startsWith("/projects") ||
  pathname.startsWith("/reports") ||
  pathname.startsWith("/sources") ||
  pathname.startsWith("/agents") ||
  pathname.startsWith("/settings") ||
  pathname.startsWith("/api/") ||
  pathname === "/favicon.ico" ||
  pathname.startsWith("/_next/");

export default function middleware(request: NextRequest) {
  if (isPublicPath(request.nextUrl.pathname)) return NextResponse.next();
  if (request.cookies.has("quorum_session") || request.headers.has("authorization")) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/sign-in", request.url));
}

export const config = {
  matcher: [
    // Skip static assets
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
