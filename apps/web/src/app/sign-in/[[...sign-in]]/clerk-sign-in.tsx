"use client";

import React from "react";
import { SignIn } from "@clerk/nextjs";

export function ClerkSignInCard() {
  return (
    <SignIn
      path="/sign-in"
      routing="path"
      signUpUrl="/sign-up"
      fallbackRedirectUrl="/projects"
      appearance={{
        variables: {
          colorPrimary: "#6366f1",
          colorBackground: "var(--surface)",
          colorText: "var(--text-primary)",
          colorTextSecondary: "var(--text-secondary)",
          colorInputBackground: "var(--surface-subtle)",
          colorInputText: "var(--text-primary)",
          borderRadius: "0.5rem",
        },
        elements: {
          card: "border border-border bg-surface shadow-xl rounded-card",
          headerTitle: "text-text-primary font-semibold text-lg",
          headerSubtitle: "text-text-secondary text-xs",
          formButtonPrimary:
            "bg-accent hover:bg-accent/90 text-accent-foreground font-medium text-xs py-2.5 rounded-control shadow-xs transition-colors",
          formFieldLabel: "text-text-secondary text-xs font-medium",
          formFieldInput:
            "border-border bg-surface-subtle text-text-primary rounded-control text-xs py-2 px-3 focus:ring-2 focus:ring-accent/20 focus:border-accent",
          footerActionLink: "text-accent hover:underline text-xs font-medium",
          identityPreviewText: "text-text-primary text-xs",
          identityPreviewEditButton: "text-accent text-xs",
        },
      }}
    />
  );
}
