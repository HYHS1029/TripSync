import "server-only";

import { cookies } from "next/headers";
import { cache } from "react";

export const SESSION_COOKIE = "tripsync_session";

export const API_BASE_URL = (
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");

export type CurrentUser = {
  id: number;
  email: string;
  username: string;
  created_at: string;
};

export const getCurrentUser = cache(async (): Promise<CurrentUser | null> => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;

  const response = await fetch(`${API_BASE_URL}/users/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
  });

  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Unable to load account");
  return response.json() as Promise<CurrentUser>;
});
