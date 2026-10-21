"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_BASE_URL, SESSION_COOKIE } from "@/lib/auth";

export type LoginState = {
  error?: string;
  email?: string;
};

export async function login(
  _previousState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = formData.get("email");
  const password = formData.get("password");
  if (typeof email !== "string" || typeof password !== "string") {
    return { error: "請輸入電子郵件與密碼。" };
  }
  const values = { email: email.trim() };
  if (
    !values.email ||
    values.email.length > 254 ||
    password.trim().length < 8 ||
    password.trim().length > 128
  ) {
    return { ...values, error: "請輸入有效的電子郵件與 8–128 字元的密碼。" };
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: values.email, password }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (response.status === 401) {
      return { ...values, error: "電子郵件或密碼不正確，請再試一次。" };
    }
    if (response.status === 422) {
      return { ...values, error: "請確認電子郵件格式與密碼長度。" };
    }
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

  redirect("/account");
}

export async function logout(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}
