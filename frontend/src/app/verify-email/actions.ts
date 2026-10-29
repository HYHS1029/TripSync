"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/auth";
import { backendRequest } from "@/lib/backend-request";
import { isEmailVerificationEnabled } from "@/lib/auth-features";
import { isEmailVerificationToken, PENDING_EMAIL_VERIFICATION } from "@/lib/email-verification";

export async function confirmEmailVerification(
  _state: { error?: string },
  form: FormData,
): Promise<{ error?: string }> {
  if (!isEmailVerificationEnabled()) return { error: "目前尚未開放信箱驗證。" };
  const jar = await cookies();
  const token = form.get("token") || jar.get(PENDING_EMAIL_VERIFICATION)?.value;
  if (!isEmailVerificationToken(token)) return { error: "缺少有效的驗證連結，請從最新一封驗證信重新開啟。" };
  jar.set(PENDING_EMAIL_VERIFICATION, token, {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "lax", path: "/verify-email", maxAge: 30 * 60,
  });
  const session = jar.get(SESSION_COOKIE)?.value;
  if (!session) redirect("/login?next=verify-email");
  let status: number;
  try {
    const response = await backendRequest("/auth/email-verification/confirm", {
      method: "POST",
      headers: { Authorization: `Bearer ${session}`, "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    status = response.status;
  } catch {
    return { error: "暫時無法連線，請稍後再試。" };
  }
  if (status === 401) redirect("/login?next=verify-email");
  if (status === 429) return { error: "驗證嘗試過於頻繁，請稍後再試。" };
  if (status === 409) return { error: "此信箱目前無法綁定，請至帳號頁確認或改用其他信箱。" };
  if (status >= 500) return { error: "驗證服務暫時無法使用，請稍後再試。" };
  if (status !== 200) return { error: "連結已過期、已被使用，或不屬於目前帳號。請確認登入帳號，或重新寄送驗證信。" };
  jar.delete({ name: PENDING_EMAIL_VERIFICATION, path: "/verify-email" });
  revalidatePath("/account");
  redirect("/account?email_verified=1");
}
