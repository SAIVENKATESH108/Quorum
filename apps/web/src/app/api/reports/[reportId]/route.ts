import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/backend-proxy";

export async function GET(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  return proxyToBackend(request, `/api/reports/${params.reportId}`);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  const body = await request.text();
  return proxyToBackend(request, `/api/reports/${params.reportId}`, {
    method: "PATCH",
    body,
  });
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { reportId: string } }
) {
  return proxyToBackend(request, `/api/reports/${params.reportId}`, {
    method: "DELETE",
  });
}
