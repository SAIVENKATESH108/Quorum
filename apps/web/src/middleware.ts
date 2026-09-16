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

const hasClerkSecret = Boolean(
  process.env.CLERK_SECRET_KEY &&
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY &&
  !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes("your_clerk")
);

export default clerkMiddleware((auth, req) => {
  // If valid Clerk keys are configured and route is not public, protect the route
  if (hasClerkSecret && !isPublicRoute(req)) {
    auth().protect();
  }
  return NextResponse.next();
});

export const config = {
  matcher: [
    // Skip static assets
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Always run for API routes
    "/(api|trpc)(.*)",
  ],
};
