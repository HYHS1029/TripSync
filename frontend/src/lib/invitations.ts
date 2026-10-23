import "server-only";

export const PENDING_INVITATION = "tripsync_invitation";
export function isInvitationToken(value: unknown): value is string {
  return typeof value === "string" && /^[A-Za-z0-9_-]{43}$/.test(value);
}
