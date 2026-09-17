"use client";

import React, { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function RootGlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error("[Quorum Root Layout Fatal Error]", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-[#14141F] text-[#ededed] flex flex-col items-center justify-center p-4 font-sans">
        <div className="w-full max-w-md text-center space-y-4">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500/10 text-rose-500">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold">System Runtime Error</h1>
          <p className="text-xs text-zinc-400">
            A fatal exception occurred outside the main layout boundary.
          </p>
          <button
            onClick={() => reset()}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Reload Application</span>
          </button>
        </div>
      </body>
    </html>
  );
}
