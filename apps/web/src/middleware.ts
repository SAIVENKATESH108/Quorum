import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Public routes that unauthenticated users and crawlers can freely access
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api(.*)",
  "/og-image.png",
  "/og-image.jpg",
  "/favicon.ico",
]);

const isProtectedRoute = createRouteMatcher([
  "/projects(.*)",
  "/reports(.*)",
  "/settings(.*)",
  "/sources(.*)",
  "/agents(.*)",
]);

const DEFAULT_CLERK_PK = "pk_test_Zmx1ZW50LXBvcnBvaXNlLTYyLmNsZXJrLmFjY291bnRzLmRldiQ";

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || DEFAULT_CLERK_PK;

export default clerkMiddleware(
  (auth, req) => {
    // Only protect explicit dashboard routes if user is not authenticated
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
