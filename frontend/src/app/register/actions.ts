"use server";

import { redirect } from "next/navigation";
import { backendRequest } from "@/lib/backend-request";

type RegisterField = "email" | "username" | "password" | "confirm_password";

export type RegisterState = {
  values: { email: string; username: string };
  error?: string;
  fieldErrors?: Partial<Record<RegisterField, string>>;
};

export async function register(
  _previousState: RegisterState,
  formData: FormData,
): Promise<RegisterState> {
  // Match the existing API's whitespace policy without returning passwords in state.
  const read = (name: string) => {
    const value = formData.get(name);
    return typeof value === "string" ? value.trim() : "";
  };
  const values = { email: read("email"), username: read("username") };
  const password = read("password");
  const confirmation = read("confirm_password");
  const fieldErrors: RegisterState["fieldErrors"] = {};

  if (!values.email || values.email.length > 254) {
    fieldErrors.email = "請輸入有效的電子郵件。";
  }
  if (!/^[A-Za-z0-9_]{3,50}$/.test(values.username)) {
    fieldErrors.username = "請使用 3–50 個英文字母、數字或底線。";
  }
  if (password.length < 8 || password.length > 128) {
    fieldErrors.password = "密碼需要 8–128 個字元。";
  }
  if (!confirmation || password !== confirmation) {
    fieldErrors.confirm_password = "兩次輸入的密碼不一致。";
  }
  if (Object.keys(fieldErrors).length > 0) {
    return { values, error: "請檢查以下欄位。", fieldErrors };
  }

  try {
    const response = await backendRequest("/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...values, password }),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });

    if (response.status === 409) {
      return {
        values,
        error: "此電子郵件或使用者名稱已被使用，請更換後再試。",
      };
    }
    if (response.status === 422) {
      const body = await response.json().catch(() => null);
      const messages = {
        email: "請輸入有效的電子郵件。",
        username: "請使用 3–50 個英文字母、數字或底線。",
        password: "密碼需要 8–128 個字元。",
      };
      if (Array.isArray(body?.detail)) {
        for (const issue of body.detail) {
          const field: unknown = issue.loc?.[1];
          if (
            field === "email" ||
            field === "username" ||
            field === "password"
          ) {
            fieldErrors[field] = messages[field];
          }
        }
      }
      return { values, error: "請檢查註冊資料。", fieldErrors };
    }
    if (response.status !== 201) {
      return { values, error: "註冊服務暫時無法使用，請稍後再試。" };
    }
  } catch {
    return { values, error: "目前無法連線至註冊服務，請稍後再試。" };
  }

  redirect(
    formData.get("next") === "join"
      ? "/login?registered=1&next=join"
      : "/login?registered=1",
  );
}
