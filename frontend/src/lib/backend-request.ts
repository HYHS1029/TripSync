import "server-only";

export const API_BASE_URL = (
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");

export async function backendRequest(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith("/") || path.startsWith("//") || path.includes("\\")) {
    throw new Error("Invalid API path");
  }
  const headers = new Headers(init.headers);
  const protectionSecret = process.env.API_PROTECTION_BYPASS;
  if (protectionSecret) headers.set("x-vercel-protection-bypass", protectionSecret);
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    // Never forward credentials or the deployment protection secret via a redirect.
    redirect: "error",
    signal: init.signal ?? AbortSignal.timeout(10_000),
  });
}
