"use server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { isTripId, TripApiError, tripRequest } from "@/lib/trips";
import type {
  Invitation,
  InvitationState,
  MutationState,
} from "@/lib/trip-types";

function memberError(error: unknown): MutationState {
  if (error instanceof TripApiError) {
    if (error.status === 401) redirect("/login");
    if (error.status === 403)
      return { error: "只有旅程建立者可以執行這項操作。" };
    if (error.status === 404)
      return { error: "找不到資料，可能已被刪除或你已無法存取。請重新整理。" };
    if (error.status === 409) return { error: "旅程建立者不能退出或被移除。" };
    if (error.status === 429)
      return { error: "這個旅程每小時最多建立 10 個邀請，請稍後再試。" };
  }
  return { error: "目前無法完成操作，請稍後重試。" };
}
export async function createInvitation(
  tripId: number,
): Promise<InvitationState> {
  if (!isTripId(tripId)) return { error: "找不到旅程。" };
  try {
    const result = await tripRequest<Invitation & { token: string }>(
      `/trips/${tripId}/invitations`,
      { method: "POST" },
    );
    revalidatePath(`/trips/${tripId}/members`);
    return { invitePath: `/join#${result.token}` };
  } catch (error) {
    return memberError(error);
  }
}
export async function revokeInvitation(
  tripId: number,
  invitationId: number,
): Promise<MutationState> {
  if (!isTripId(tripId) || !isTripId(invitationId))
    return { error: "找不到邀請。" };
  try {
    await tripRequest<void>(`/trips/${tripId}/invitations/${invitationId}`, {
      method: "DELETE",
    });
  } catch (error) {
    return memberError(error);
  }
  revalidatePath(`/trips/${tripId}/members`);
  return { success: "邀請已撤銷。" };
}
export async function removeMember(
  tripId: number,
  userId: number,
): Promise<MutationState> {
  if (!isTripId(tripId) || !isTripId(userId)) return { error: "找不到成員。" };
  try {
    await tripRequest<void>(`/trips/${tripId}/members/${userId}`, {
      method: "DELETE",
    });
  } catch (error) {
    return memberError(error);
  }
  revalidatePath(`/trips/${tripId}`);
  revalidatePath(`/trips/${tripId}/members`);
  return { success: "成員已移除。" };
}
export async function leaveTrip(tripId: number): Promise<MutationState> {
  if (!isTripId(tripId)) return { error: "找不到旅程。" };
  try {
    await tripRequest<void>(`/trips/${tripId}/members/me`, {
      method: "DELETE",
    });
  } catch (error) {
    return memberError(error);
  }
  revalidatePath("/trips");
  redirect("/trips");
}
