import { NextRequest, NextResponse } from "next/server";

// Public paths accessible without authentication:
// - Landing page, auth routes, static assets, and explicit public report pages.
// Protected dashboard paths (/projects, /reports index, /sources, /agents, /settings)
// require a valid session cookie or authorization header, redirecting unauthenticated
// visitors to /sign-in (which includes one-click Guest Judge onboarding).
const isPublicPath = (pathname: string) =>
  pathname === "/" ||
  pathname.startsWith("/sign-in") ||
  pathname.startsWith("/sign-up") ||
  pathname.startsWith("/api/") ||
  pathname === "/favicon.ico" ||
  pathname.startsWith("/_next/") ||
  // Explicitly public report pages (UUID or report slug)
  /^\/reports\/[0-9a-fA-F-]+$/.test(pathname);


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
