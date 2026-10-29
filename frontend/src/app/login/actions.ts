"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/auth";
import { backendRequest } from "@/lib/backend-request";
import { PENDING_INVITATION } from "@/lib/invitations";
import { getDevelopmentCredentials } from "@/lib/dev-login";
import { PENDING_EMAIL_VERIFICATION } from "@/lib/email-verification";
import { isEmailVerificationEnabled } from "@/lib/auth-features";

export type LoginState = {
  error?: string;
  identifier?: string;
};

export async function login(
  _previousState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const identifier = formData.get("identifier");
  const password = formData.get("password");
  if (typeof identifier !== "string" || typeof password !== "string") {
    return { error: "請輸入帳號與密碼。" };
  }
  const values = { identifier: identifier.trim() };
  if (
    values.identifier.length < 3 ||
    values.identifier.length > 254 ||
    password.trim().length < 8 ||
    password.trim().length > 128
  ) {
    return { ...values, error: "請輸入有效的帳號與 8–128 字元的密碼。" };
  }

  try {
    const response = await backendRequest("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: values.identifier, password }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (response.status === 401) {
      return { ...values, error: "帳號或密碼不正確，請再試一次。" };
    }
    if (response.status === 422) {
      return { ...values, error: "請確認帳號格式與密碼長度。" };
    }
    if (response.status === 429) return { ...values, error: "登入嘗試過於頻繁，請稍後再試。" };
    if (!response.ok) {
      return { ...values, error: "登入服務暫時無法使用，請稍後再試。" };
    }
    const result: {
      access_token: string;
      token_type: string;
      expires_in: number;
    } = await response.json();
    if (
      typeof result.access_token !== "string" ||
      !result.access_token ||
      result.token_type !== "bearer" ||
      !Number.isInteger(result.expires_in) ||
      result.expires_in <= 0
    ) {
      return { ...values, error: "登入服務暫時無法使用，請稍後再試。" };
    }

    (await cookies()).set(SESSION_COOKIE, result.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: result.expires_in,
    });
  } catch {
    return { ...values, error: "目前無法連線至登入服務，請稍後再試。" };
  }

  const next = formData.get("next");
  redirect(next === "join" ? "/join" : next === "verify-email" && isEmailVerificationEnabled() ? "/verify-email" : "/account");
}

export async function logout(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  (await cookies()).delete(PENDING_INVITATION);
  (await cookies()).delete({ name: PENDING_EMAIL_VERIFICATION, path: "/verify-email" });
  redirect("/login");
}

export async function developmentLogin(
  _previousState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  // Check again on POST: hiding the button is not authorization.
  const credentials = await getDevelopmentCredentials(true);
  if (!credentials) return { error: "開發者快速登入僅供已設定的本機開發環境使用。" };

  const loginData = new FormData();
  loginData.set("identifier", credentials.identifier);
  loginData.set("password", credentials.password);
  if (formData.get("next") === "join") loginData.set("next", "join");
  if (formData.get("next") === "verify-email") loginData.set("next", "verify-email");
  const result = await login({}, loginData);
  // Credentials and backend errors must never be serialized to the browser.
  return { error: result.error ? "測試帳號登入失敗，請確認後端已啟動，並重新執行本機帳號設定。" : undefined };
}
