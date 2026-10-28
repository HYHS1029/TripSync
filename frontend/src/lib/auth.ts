import "server-only";

import { cookies } from "next/headers";
import { cache } from "react";
import { backendRequest } from "./backend-request";

export const SESSION_COOKIE = "tripsync_session";

export { API_BASE_URL } from "./backend-request";

export type CurrentUser = {
  id: number;
  email: string;
  username: string;
  created_at: string;
};

export const getCurrentUser = cache(async (): Promise<CurrentUser | null> => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;

  const response = await backendRequest("/users/me", {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal: AbortSignal.timeout(10_000),
  });

  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Unable to load account");
  return response.json() as Promise<CurrentUser>;
});
