import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";
import { TanStackQueryProvider } from "@/components/query-provider";
import { ThemeProvider } from "@/components/theme-provider";
import { ToastProvider } from "@/components/ui/toast";
import { AuthSync } from "@/components/auth-sync";

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
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://quorum-research.vercel.app"
  ),
  title: {
    default: "Quorum — Autonomous Multi-Agent AI Research & Verification Platform",
    template: "%s | Quorum Research",
  },
  description:
    "Collaborative multi-agent intelligence platform that decomposes research queries into dependency-governed DAGs, validates claims against peer-reviewed DOIs, and synthesizes publication-grade research papers.",
  keywords: [
    "multi-agent AI",
    "autonomous research swarm",
    "scientific evidence synthesis",
    "peer-reviewed DOI verification",
    "Byzantine fault tolerance",
    "DAG consensus",
    "ReportLab PDF compilation",
    "academic intelligence",
  ],
  authors: [{ name: "V.A. Sai Venkatesh", url: "https://quorum-research.vercel.app" }],
  creator: "V.A. Sai Venkatesh",
  publisher: "Quorum Autonomous Systems",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Quorum — Autonomous Multi-Agent AI Research & Verification Platform",
    description:
      "Transform complex research queries into rigorously cited, fact-checked intelligence reports in minutes using parallel agent swarms.",
    url: "https://quorum-research.vercel.app",
    siteName: "Quorum",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "Quorum — Autonomous Multi-Agent AI Research & Verification Platform",
      },
    ],
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Quorum — Autonomous Multi-Agent AI Research & Verification Platform",
    description:
      "Transform complex research queries into rigorously cited, fact-checked intelligence reports in minutes using parallel agent swarms.",
    images: ["/og-image.png"],
    creator: "@QuorumAI",
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "32x32" },
      { url: "/quorum-logo.png", type: "image/png", sizes: "1600x1600" },
      { url: "/favicon.svg", type: "image/svg+xml" },
    ],
    shortcut: "/favicon.ico",
    apple: [{ url: "/quorum-logo.png", sizes: "1600x1600", type: "image/png" }],
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
      <html lang="en" suppressHydrationWarning>
        <body
          className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-bg text-text-primary antialiased selection:bg-accent/20 selection:text-accent`}
        >
          <AuthSync />
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
