"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { isTripId, TripApiError, tripRequest } from "@/lib/trips";
import type {
  DeleteTripState,
  Trip,
  TripFormState,
  TripValues,
} from "@/lib/trip-types";

function readValues(form: FormData): TripValues {
  const read = (name: string) => {
    const value = form.get(name);
    return typeof value === "string" ? value.trim() : "";
  };
  return {
    name: read("name"),
    destination: read("destination"),
    start_date: read("start_date"),
    end_date: read("end_date"),
    description: read("description"),
  };
}

function errorState(error: unknown, values: TripValues): TripFormState {
  if (error instanceof TripApiError) {
    if (error.status === 401) redirect("/login");
    if (error.status === 403)
      return { values, error: "只有旅程建立者可以編輯這個旅程。" };
    if (error.status === 404)
      return { values, error: "找不到旅程，可能已被刪除或你已無法存取。" };
    if (error.status === 422) {
      return {
        values,
        error: "請檢查欄位內容與日期範圍。",
        fieldErrors: error.fieldErrors,
      };
    }
  }
  return { values, error: "暫時無法儲存旅程，請稍後再試。" };
}

export async function createTrip(
  _previousState: TripFormState,
  form: FormData,
): Promise<TripFormState> {
  const values = readValues(form);
  let trip: Trip;
  try {
    trip = await tripRequest<Trip>("/trips", {
      method: "POST",
      body: JSON.stringify(values),
    });
  } catch (error) {
    return errorState(error, values);
  }
  revalidatePath("/trips");
  redirect(`/trips/${trip.id}`);
}

export async function updateTrip(
  tripId: number,
  _previousState: TripFormState,
  form: FormData,
): Promise<TripFormState> {
  const values = readValues(form);
  if (!isTripId(tripId)) return { values, error: "找不到旅程。" };
  try {
    await tripRequest<Trip>(`/trips/${tripId}`, {
      method: "PATCH",
      body: JSON.stringify(values),
    });
  } catch (error) {
    return errorState(error, values);
  }
  revalidatePath("/trips");
  revalidatePath(`/trips/${tripId}`);
  redirect(`/trips/${tripId}`);
}

export async function deleteTrip(tripId: number): Promise<DeleteTripState> {
  if (!isTripId(tripId)) return { error: "找不到旅程。" };
  try {
    await tripRequest<void>(`/trips/${tripId}`, { method: "DELETE" });
  } catch (error) {
    if (error instanceof TripApiError) {
      if (error.status === 401) redirect("/login");
      if (error.status === 403)
        return { error: "只有旅程建立者可以刪除這個旅程。" };
      if (error.status !== 404)
        return { error: "暫時無法刪除旅程，請稍後再試。" };
    } else {
      return { error: "暫時無法刪除旅程，請稍後再試。" };
    }
    // Already removed, or access was revoked. Return to the user's own list.
  }
  revalidatePath("/trips");
  revalidatePath(`/trips/${tripId}`);
  redirect("/trips");
}
