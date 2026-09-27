import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  return proxyToBackend(request, `/api/projects/${params.projectId}`);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  const body = await request.text();
  return proxyToBackend(request, `/api/projects/${params.projectId}`, {
    method: "PATCH",
    body,
  });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { projectId: string } }
) {
  return proxyToBackend(request, `/api/projects/${params.projectId}`, {
    method: "DELETE",
  });
}
