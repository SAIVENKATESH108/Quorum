import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Only the landing page and Clerk flows are public. All workspace and API data
// must be associated with an authenticated Clerk user.
const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/og-image.png",
  "/og-image.jpg",
  "/favicon.ico",
]);

const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export default clerkMiddleware(
  (auth, req) => {
    if (!isPublicRoute(req)) {
      auth().protect({
        unauthenticatedUrl: new URL("/sign-in", req.url).toString(),
      });
    }
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
