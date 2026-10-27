"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { isTripId, TripApiError, tripRequest } from "@/lib/trips";
import type { MutationState } from "@/lib/trip-types";
import type { MapData, Place, RouteResult } from "@/lib/planner-types";

function message(error: unknown): string {
  if (error instanceof TripApiError) {
    if (error.status === 401) redirect("/login");
    if (error.status === 404) return "找不到旅程或活動，請重新整理確認。";
    if (error.status === 503) return "地圖服務尚未啟用或目前無法連線。";
    if (error.status === 502) return "Google Maps 暫時無法回應，請稍後重試。";
    if (error.status === 422)
      return "請確認地點、日期與出發時間；整趟地圖最多顯示 100 個不同地點。";
  }
  return "操作未完成，請重新整理後重試。";
}
export async function searchPlaces(
  tripId: number,
  query: string,
): Promise<{ places?: Place[]; error?: string }> {
  if (!isTripId(tripId) || query.trim().length < 2 || query.length > 200)
    return { error: "請輸入 2–200 字的地點名稱。" };
  try {
    return {
      places: await tripRequest<Place[]>(
        `/trips/${tripId}/places/search?q=${encodeURIComponent(query.trim())}`,
      ),
    };
  } catch (error) {
    return { error: message(error) };
  }
}
export async function loadMapPoints(
  tripId: number,
  day: string,
  allDays: boolean,
): Promise<{ data?: MapData; error?: string }> {
  if (!isTripId(tripId)) return { error: "找不到旅程。" };
  try {
    return {
      data: await tripRequest<MapData>(
        `/trips/${tripId}/map-points?day=${encodeURIComponent(day)}&all_days=${allDays}`,
      ),
    };
  } catch (error) {
    return { error: message(error) };
  }
}
export async function queryRoute(
  tripId: number,
  input: {
    origin_id: number;
    destination_id: number;
    day: string;
    mode: string;
    departure_time: string;
  },
): Promise<{ route?: RouteResult; error?: string }> {
  if (!isTripId(tripId)) return { error: "找不到旅程。" };
  try {
    return {
      route: await tripRequest<RouteResult>(`/trips/${tripId}/routes`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    };
  } catch (error) {
    return { error: message(error) };
  }
}
export async function reorderActivities(
  tripId: number,
  day: string,
  ids: number[],
): Promise<MutationState> {
  if (!isTripId(tripId)) return { error: "找不到旅程。" };
  try {
    await tripRequest(`/trips/${tripId}/activities/reorder`, {
      method: "POST",
      body: JSON.stringify({ activity_date: day, activity_ids: ids }),
    });
  } catch (error) {
    return {
      error:
        error instanceof TripApiError && error.status === 409
          ? "活動已被旅伴修改，請重新整理再排序。"
          : message(error),
    };
  }
  revalidatePath(`/trips/${tripId}`);
  return { success: "順序已更新。" };
}
