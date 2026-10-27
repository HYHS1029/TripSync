import "server-only";

import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { API_BASE_URL, SESSION_COOKIE } from "@/lib/auth";
import type { Trip, TripValues } from "@/lib/trip-types";

export class TripApiError extends Error {
  constructor(
    public status: number,
    public fieldErrors: Record<string, string> = {},
  ) {
    super("Trip request failed");
  }
}

export function isTripId(value: string | number): boolean {
  return /^[1-9]\d{0,9}$/.test(String(value)) && Number(value) <= 2_147_483_647;
}

export async function tripRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
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
    const fields: Record<string, string> = {};
    if (response.status === 422) {
      const body = await response.json().catch(() => null);
      const messages: Record<string, string> = {
        name: "請輸入 1–100 字元的旅程名稱。",
        destination: "請輸入 1–200 字元的目的地。",
        start_date: "請輸入有效的出發日期。",
        end_date: "請確認結束日期有效，且不早於出發日期。",
        description: "說明最多可輸入 2000 字元。",
        title: "請輸入 1–100 字元的活動名稱。",
        activity_date: "請選擇旅程日期範圍內的日期。",
        start_time: "請輸入有效的開始時間。",
        end_time: "請確認結束時間不早於開始時間。",
        location: "地點最多可輸入 200 字元。",
        notes: "備註最多可輸入 2000 字元。",
        timezone: "請輸入有效的 IANA 時區，例如 Asia/Tokyo。",
        currency: "請選擇支援的記帳幣別。",
        stay_until: "退房日期需在入住日之後，且位於旅程日期範圍內。",
      };
      if (Array.isArray(body?.detail)) {
        for (const issue of body.detail) {
          const field = issue.loc?.[1] as keyof TripValues;
          if (field && messages[field]) {
            fields[field] =
              issue.type === "activity_date_range"
                ? "旅程日期必須涵蓋所有已安排的活動，請先調整活動日期。"
                : messages[field];
          }
        }
      }
    }
    throw new TripApiError(response.status, fields);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function handlePageError(error: unknown): never {
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
