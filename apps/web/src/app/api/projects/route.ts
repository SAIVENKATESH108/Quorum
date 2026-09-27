import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export async function GET(request: NextRequest) {
  return proxyToBackend(request, "/api/projects");
}

export async function POST(request: NextRequest) {
  const body = await request.text();
  return proxyToBackend(request, "/api/projects", {
    method: "POST",
    body,
  });
}
