"use server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { isTripId, TripApiError, tripRequest } from "@/lib/trips";
import type {
  Activity,
  ActivityFormState,
  ActivityValues,
  MutationState,
} from "@/lib/trip-types";

function readValues(form: FormData): ActivityValues {
  const read = (name: string) => {
    const value = form.get(name);
    return typeof value === "string" ? value.trim() : "";
  };
  return {
    title: read("title"),
    activity_date: read("activity_date"),
    start_time: read("start_time"),
    end_time: read("end_time"),
    location: read("location"),
    notes: read("notes"),
  };
}
export async function saveActivity(
  tripId: number,
  activityId: number | null,
  _state: ActivityFormState,
  form: FormData,
): Promise<ActivityFormState> {
  const values = readValues(form);
  if (!isTripId(tripId) || (activityId !== null && !isTripId(activityId)))
    return { values, error: "找不到旅程或活動。" };
  let activity: Activity;
  try {
    activity = await tripRequest<Activity>(
      `/trips/${tripId}/activities${activityId === null ? "" : `/${activityId}`}`,
      {
        method: activityId === null ? "POST" : "PUT",
        body: JSON.stringify({
          ...values,
          start_time: values.start_time || null,
          end_time: values.end_time || null,
        }),
      },
    );
  } catch (error) {
    if (error instanceof TripApiError) {
      if (error.status === 401) redirect("/login");
      if (error.status === 404)
        return {
          values,
          error: "找不到活動，可能已刪除或你已不在這趟旅程中。",
        };
      if (error.status === 422)
        return {
          values,
          error: "請確認日期在旅程範圍內，且結束時間不早於開始時間。",
          fieldErrors: error.fieldErrors,
        };
      if (error.status === 409)
        return {
          values,
          error: "每趟旅程最多安排 500 個活動，請先整理既有活動。",
        };
    }
    return { values, error: "暫時無法儲存活動，請稍後重試。" };
  }
  revalidatePath(`/trips/${tripId}`);
  redirect(`/trips/${tripId}?day=${activity.activity_date}`);
}
export async function deleteActivity(
  tripId: number,
  activityId: number,
  day: string,
): Promise<MutationState> {
  if (!isTripId(tripId) || !isTripId(activityId))
    return { error: "找不到活動。" };
  try {
    await tripRequest<void>(`/trips/${tripId}/activities/${activityId}`, {
      method: "DELETE",
    });
  } catch (error) {
    if (error instanceof TripApiError && error.status === 401)
      redirect("/login");
    return { error: "無法刪除活動，請重新整理確認權限與資料是否仍有效。" };
  }
  revalidatePath(`/trips/${tripId}`);
  redirect(`/trips/${tripId}?day=${encodeURIComponent(day)}`);
}
