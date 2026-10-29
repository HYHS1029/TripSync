import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { isEmailVerificationEnabled } from "@/lib/auth-features";
import { getDevelopmentCredentials } from "@/lib/dev-login";
import LoginForm from "./login-form";
import DevelopmentLoginForm from "./dev-login-form";

export const metadata: Metadata = { title: "登入 | TripSync" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string; next?: string }>;
}) {
  const { registered, next } = await searchParams;
  const returnToJoin = next === "join";
  const emailVerificationEnabled = isEmailVerificationEnabled();
  const nextPage = returnToJoin ? "join" : next === "verify-email" && emailVerificationEnabled ? "verify-email" : undefined;
  // Keep the form available if the API is temporarily offline.
  const user = await getCurrentUser().catch(() => null);
  if (user) redirect(nextPage === "join" ? "/join" : nextPage === "verify-email" ? "/verify-email" : "/account");
  const developmentLoginEnabled = Boolean(await getDevelopmentCredentials());

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6 py-12 dark:bg-zinc-950">
      <div className="w-full max-w-md">
        <Link
          href="/"
          className="mb-8 inline-block text-lg font-bold tracking-tight text-teal-700 dark:text-teal-400"
        >
          TripSync
        </Link>
        <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
          <h1 className="text-3xl font-bold tracking-tight">歡迎回來</h1>
          <p className="mb-8 mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            {emailVerificationEnabled
              ? "使用者名稱或已驗證的電子郵件，搭配密碼即可登入。既有帳號若尚未驗證信箱，請先使用使用者名稱。"
              : "使用註冊時設定的使用者名稱與密碼登入 TripSync。"}
          </p>
          {registered === "1" && (
            <p
              role="status"
              className="mb-6 rounded-xl bg-teal-50 p-3 text-sm text-teal-800 dark:bg-teal-950 dark:text-teal-300"
            >
              帳號建立成功，請使用新帳號登入。{emailVerificationEnabled && "電子郵件可於登入後驗證。"}
            </p>
          )}
          {returnToJoin && (
            <p className="mb-4 text-sm text-teal-700 dark:text-teal-300">
              登入後會回到旅程邀請，讓你確認加入。
            </p>
          )}
          {nextPage === "verify-email" && <p className="mb-4 text-sm text-teal-700 dark:text-teal-300">請登入提出信箱驗證申請的帳號，登入後會回到驗證頁面。</p>}
          <LoginForm next={nextPage} emailVerificationEnabled={emailVerificationEnabled} />
          {developmentLoginEnabled && <DevelopmentLoginForm next={nextPage} />}
          <p className="mt-6 text-center text-sm text-zinc-600 dark:text-zinc-400">
            還沒有帳號？{" "}
            <Link
              href={returnToJoin ? "/register?next=join" : "/register"}
              className="font-medium text-teal-700 underline-offset-4 hover:underline dark:text-teal-400"
            >
              註冊
            </Link>
          </p>
        </section>
        <p className="mt-6 text-center text-sm text-zinc-500">
          讓每一趟旅行，都從一起出發開始。
        </p>
      </div>
    </main>
  );
}
