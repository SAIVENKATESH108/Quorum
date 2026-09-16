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
const DEFAULT_CLERK_SK = "sk_test_NOKlelaDB9z4m8gwrGHt3arkTAVXLw02vHIXnni3P2";

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || DEFAULT_CLERK_PK;
const secretKey = process.env.CLERK_SECRET_KEY || DEFAULT_CLERK_SK;

export default clerkMiddleware(
  (auth, req) => {
    // If route is protected, enforce authentication
    if (!isPublicRoute(req)) {
      auth().protect();
    }
    return NextResponse.next();
  },
  {
    publishableKey,
    secretKey,
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
