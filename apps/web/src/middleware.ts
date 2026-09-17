import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Public routes that unauthenticated users, judges, and crawlers can freely access
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api(.*)",
  "/reports(.*)",
  "/sources(.*)",
  "/og-image.png",
  "/og-image.jpg",
  "/favicon.ico",
]);

const isProtectedRoute = createRouteMatcher([
  "/settings(.*)",
  "/agents(.*)",
]);

const DEFAULT_CLERK_PK = "pk_test_Zmx1ZW50LXBvcnBvaXNlLTYyLmNsZXJrLmFjY291bnRzLmRldiQ";
const GUEST_COOKIE_NAME = "quorum_guest_session";

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || DEFAULT_CLERK_PK;

export default clerkMiddleware(
  (auth, req) => {
    // 1. Check for server-side guest judge session
    const hasGuestCookie = req.cookies.has(GUEST_COOKIE_NAME);
    const hasGuestParam = req.nextUrl.searchParams.get("guest") === "true";
    const isEvaluatingDirectly =
      req.nextUrl.pathname.startsWith("/reports") ||
      req.nextUrl.pathname.startsWith("/projects") ||
      req.nextUrl.pathname.startsWith("/sources");

    if (hasGuestCookie || hasGuestParam || isEvaluatingDirectly) {
      const res = NextResponse.next();
      if (!hasGuestCookie) {
        res.cookies.set({
          name: GUEST_COOKIE_NAME,
          value: `judge-${Date.now()}`,
          maxAge: 60 * 60 * 24, // 24 hours
          path: "/",
          httpOnly: true,
          secure: process.env.NODE_ENV === "production",
          sameSite: "lax",
        });
      }
      return res;
    }

    // 2. Only protect explicit dashboard routes if user is not authenticated and not a guest judge
    if (isProtectedRoute(req) && !isPublicRoute(req)) {
      auth().protect({
        unauthenticatedUrl: new URL("/sign-in", req.url).toString(),
      });
    }

    return NextResponse.next();
  },
  {
    publishableKey,
  }
);

export const config = {
  matcher: [
    // Skip static assets
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
