import { backendRequest } from "@/lib/backend-request";

export async function GET() {
  try {
    const response = await backendRequest("/health");
    if (!response.ok || (await response.json()).status !== "ok") throw new Error("Unavailable");
    return Response.json({ status: "ok" }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ status: "unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
