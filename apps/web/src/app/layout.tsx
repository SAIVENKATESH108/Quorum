import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { TanStackQueryProvider } from "@/components/query-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { ToastProvider } from "@/components/ui/toast";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Quorum — AI agents that research, verify, and write",
  description:
    "Collaborative multi-agent intelligence platform that decomposes research queries, validates facts across verified sources, and generates structured reports.",
  openGraph: {
    title: "Quorum — AI agents that research, verify, and write",
    description:
      "Collaborative multi-agent intelligence platform that decomposes research queries, validates facts across verified sources, and generates structured reports.",
    siteName: "Quorum",
    type: "website",
    locale: "en_US",
  },
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAFAF8" },
    { media: "(prefers-color-scheme: dark)", color: "#14141F" },
  ],
};

import { ClerkProvider } from "@clerk/nextjs";
import { AuthSync } from "@/components/auth-sync";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      publishableKey={
        process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
        "pk_test_Zmx1ZW50LXBvcnBvaXNlLTYyLmNsZXJrLmFjY291bnRzLmRldiQ"
      }
    >
      <AuthSync />
      <html lang="en" suppressHydrationWarning>
        <body
          className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-bg text-text-primary antialiased selection:bg-accent/20 selection:text-accent`}
        >
          <TanStackQueryProvider>
            <ThemeProvider>
              <ToastProvider>{children}</ToastProvider>
            </ThemeProvider>
          </TanStackQueryProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}

