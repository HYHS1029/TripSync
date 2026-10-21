import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { API_BASE_URL, SESSION_COOKIE } from "@/lib/auth";
import type { Trip, TripValues } from "@/lib/trip-types";

export class TripApiError extends Error {
  constructor(
    public status: number,
    public fieldErrors: Partial<Record<keyof TripValues, string>> = {},
  ) {
    super("Trip request failed");
  }
}

export function isTripId(value: string | number): boolean {
  return /^[1-9]\d{0,9}$/.test(String(value)) && Number(value) <= 2_147_483_647;
}

export async function tripRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) throw new TripApiError(401);

  let response: Response;
  try {
    const headers = new Headers(init?.headers);
    headers.set("Authorization", `Bearer ${token}`);
    if (init?.body) headers.set("Content-Type", "application/json");
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    throw new TripApiError(503);
  }

  if (!response.ok) {
    const fields: Partial<Record<keyof TripValues, string>> = {};
    if (response.status === 422) {
      const body = await response.json().catch(() => null);
      const messages: Record<string, string> = {
        name: "請輸入 1–100 字元的旅程名稱。",
        destination: "請輸入 1–200 字元的目的地。",
        start_date: "請輸入有效的出發日期。",
        end_date: "請確認結束日期有效，且不早於出發日期。",
        description: "說明最多可輸入 2000 字元。",
      };
      if (Array.isArray(body?.detail)) {
        for (const issue of body.detail) {
          const field = issue.loc?.[1] as keyof TripValues;
          if (field && messages[field]) fields[field] = messages[field];
        }
      }
    }
    throw new TripApiError(response.status, fields);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function handlePageError(error: unknown): never {
  if (error instanceof TripApiError) {
    if (error.status === 401) redirect("/login");
    if (error.status === 404) notFound();
  }
  throw error;
}

export async function getTrips(): Promise<Trip[]> {
  try {
    return await tripRequest<Trip[]>("/trips");
  } catch (error) {
    handlePageError(error);
  }
}

export async function getTrip(id: string): Promise<Trip> {
  if (!isTripId(id)) notFound();
  try {
    return await tripRequest<Trip>(`/trips/${id}`);
  } catch (error) {
    handlePageError(error);
  }
}
