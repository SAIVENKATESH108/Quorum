"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { setAuthTokenGetter } from "@/lib/api-client";

export function AuthSync() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (isLoaded) {
      setAuthTokenGetter(async () => {
        if (!isSignedIn) return null;
        return await getToken();
      });
    }
  }, [getToken, isLoaded, isSignedIn]);

  return null;
}
