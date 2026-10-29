"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/auth";
import { backendRequest } from "@/lib/backend-request";
import { isEmailVerificationEnabled } from "@/lib/auth-features";

export type EmailVerificationState = { email?: string; error?: string; message?: string };

export async function requestEmailVerification(
  _state: EmailVerificationState,
  form: FormData,
): Promise<EmailVerificationState> {
  if (!isEmailVerificationEnabled()) return { error: "目前尚未開放信箱驗證。" };
  const email = String(form.get("email") ?? "").trim();
  const password = String(form.get("password") ?? "");
  if (!email || email.length > 254 || password.trim().length < 8 || password.trim().length > 128) {
    return { email, error: "請輸入有效的電子郵件與目前密碼。" };
  }
  const session = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!session) redirect("/login");
  try {
    const response = await backendRequest("/auth/email-verification/request", {
      method: "POST",
      headers: { Authorization: `Bearer ${session}`, "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      signal: AbortSignal.timeout(30_000),
    });
    if (response.status === 401) return { email, error: "密碼不正確，或登入已過期，請確認後再試。" };
    if (response.status === 422) return { email, error: "請確認電子郵件格式與密碼長度。" };
    if (response.status === 409) return { email, error: "此信箱已完成驗證，無需重寄。" };
    if (response.status === 429) return { email, error: "寄送過於頻繁，請稍後再試。" };
    if (response.status !== 202) return { email, error: "暫時無法寄送驗證信，請稍後再試。" };
  } catch {
    return { email, error: "無法連線至寄信服務，請稍後再試。" };
  }
  revalidatePath("/account");
  return { email, message: "驗證信已寄出，請使用最新一封信的連結完成驗證。也請檢查垃圾郵件。" };
}
