import "server-only";
import { notFound } from "next/navigation";
import { handlePageError, isTripId, tripRequest } from "./trips";
import type { Activity, Invitation, TripMember } from "./trip-types";

export async function getMembers(tripId: string): Promise<TripMember[]> {
  try {
    return await tripRequest<TripMember[]>(`/trips/${tripId}/members`);
  } catch (error) {
    handlePageError(error);
  }
}
export async function getInvitations(tripId: string): Promise<Invitation[]> {
  try {
    return await tripRequest<Invitation[]>(`/trips/${tripId}/invitations`);
  } catch (error) {
    handlePageError(error);
  }
}
export async function getActivities(tripId: string): Promise<Activity[]> {
  try {
    return await tripRequest<Activity[]>(`/trips/${tripId}/activities`);
  } catch (error) {
    handlePageError(error);
  }
}
export async function getActivity(
  tripId: string,
  activityId: string,
): Promise<Activity> {
  if (!isTripId(activityId)) notFound();
  try {
    return await tripRequest<Activity>(
      `/trips/${tripId}/activities/${activityId}`,
    );
  } catch (error) {
    handlePageError(error);
  }
}
