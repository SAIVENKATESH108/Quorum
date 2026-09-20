import { NextRequest, NextResponse } from "next/server";

// Only the landing page and native auth flows are public. All workspace and API data
// must be associated with an authenticated Clerk user.
const isPublicPath = (pathname: string) =>
  pathname === "/" || pathname.startsWith("/sign-in") || pathname.startsWith("/sign-up") ||
  pathname.startsWith("/api/auth") || pathname === "/favicon.ico" || pathname.startsWith("/_next/");

export default function middleware(request: NextRequest) {
  if (isPublicPath(request.nextUrl.pathname)) return NextResponse.next();
  if (!request.cookies.has("quorum_session")) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    // Skip static assets
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
