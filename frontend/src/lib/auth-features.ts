import "server-only";

export function isEmailVerificationEnabled(): boolean {
  return process.env.EMAIL_VERIFICATION_ENABLED === "true";
}
