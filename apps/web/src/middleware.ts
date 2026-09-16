import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Public routes that unauthenticated users can access
const isPublicRoute = createRouteMatcher([
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api(.*)",
  "/_next(.*)",
  "/favicon.ico",
]);

const DEFAULT_CLERK_PK = "pk_test_Zmx1ZW50LXBvcnBvaXNlLTYyLmNsZXJrLmFjY291bnRzLmRldiQ";

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || DEFAULT_CLERK_PK;

export default clerkMiddleware(
  (auth, req) => {
    // If route is protected, redirect to local /sign-in
    if (!isPublicRoute(req)) {
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
