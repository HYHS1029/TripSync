"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { PENDING_INVITATION, isInvitationToken } from "@/lib/invitations";
import { TripApiError, tripRequest } from "@/lib/trips";
import type { MutationState, Trip } from "@/lib/trip-types";

export async function joinTrip(
  _state: MutationState,
  form: FormData,
): Promise<MutationState> {
  const jar = await cookies();
  const supplied = form.get("token");
  const token = supplied || jar.get(PENDING_INVITATION)?.value;
  if (!isInvitationToken(token))
    return { error: "缺少有效的邀請連結，請向旅程建立者索取新的連結。" };
  // Keep the credential out of auth URLs and client-side storage during login.
  jar.set(PENDING_INVITATION, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 15 * 60,
  });
  let trip: Trip;
  try {
    trip = await tripRequest<Trip>("/invitations/accept", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  } catch (error) {
    if (error instanceof TripApiError) {
      if (error.status === 401) redirect("/login?next=join");
      if (error.status === 404) {
        jar.delete(PENDING_INVITATION);
        return {
          error: "邀請已失效、已被使用或已撤銷，請向旅程建立者索取新的連結。",
        };
      }
      if (error.status === 409)
        return { error: "這趟旅程已達成員上限，請聯絡旅程建立者。" };
    }
    return { error: "暫時無法加入，請稍後再按一次確認。" };
  }
  jar.delete(PENDING_INVITATION);
  revalidatePath("/trips");
  redirect(`/trips/${trip.id}`);
}
