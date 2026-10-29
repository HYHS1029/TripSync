import "server-only";

import { headers } from "next/headers";
import { API_BASE_URL } from "./auth";
import { allowsDevelopmentLogin } from "./dev-login-policy";

export async function getDevelopmentCredentials(requireOrigin = false) {
  if (!allowsDevelopmentLogin({
    nodeEnv: process.env.NODE_ENV,
    enabled: process.env.TRIPSYNC_DEV_LOGIN_ENABLED,
    apiBaseUrl: API_BASE_URL,
  }, await headers(), requireOrigin)) return null;

  const email = process.env.TRIPSYNC_DEV_LOGIN_EMAIL;
  const password = process.env.TRIPSYNC_DEV_LOGIN_PASSWORD;
  if (email !== "developer@example.com" || !password || password.length < 32 || password.length > 128) {
    return null;
  }
  return { identifier: "TripSync 開發者", password };
}
