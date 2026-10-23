import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import LoginForm from "./login-form";

export const metadata: Metadata = { title: "登入 | TripSync" };

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ registered?: string; next?: string }>;
}) {
  const { registered, next } = await searchParams;
  const returnToJoin = next === "join";
  // Keep the form available if the API is temporarily offline.
  const user = await getCurrentUser().catch(() => null);
  if (user) redirect(returnToJoin ? "/join" : "/account");

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
            使用已註冊的電子郵件與密碼登入 TripSync。
          </p>
          {registered === "1" && (
            <p
              role="status"
              className="mb-6 rounded-xl bg-teal-50 p-3 text-sm text-teal-800 dark:bg-teal-950 dark:text-teal-300"
            >
              帳號建立成功，請使用新帳號登入。
            </p>
          )}
          {returnToJoin && (
            <p className="mb-4 text-sm text-teal-700 dark:text-teal-300">
              登入後會回到旅程邀請，讓你確認加入。
            </p>
          )}
          <LoginForm returnToJoin={returnToJoin} />
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
