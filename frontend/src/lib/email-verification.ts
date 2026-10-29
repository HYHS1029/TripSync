export const PENDING_EMAIL_VERIFICATION = "tripsync_email_verification";

export function isEmailVerificationToken(value: unknown): value is string {
  return typeof value === "string" && value.length === 43 && /^[A-Za-z0-9_-]{43}$/.test(value);
}
