import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { getCurrentUser } from "@/lib/auth";
import { isEmailVerificationEnabled } from "@/lib/auth-features";
import VerifyEmailForm from "./verify-email-form";

export const metadata: Metadata = { title: "驗證電子郵件 | TripSync", robots: { index: false, follow: false } };

export default async function VerifyEmailPage() {
  await connection();
  if (!isEmailVerificationEnabled()) notFound();
  const user = await getCurrentUser();
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6 py-12 dark:bg-zinc-950">
      <section className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <Link href="/" className="text-lg font-bold text-teal-700 dark:text-teal-400">TripSync</Link>
        <h1 className="mt-6 text-3xl font-bold">驗證電子郵件</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">{user ? `目前登入：${user.username}。請確認這是提出驗證申請的帳號，再按下確認。` : "請使用提出驗證申請的帳號登入，再確認綁定信箱。"}</p>
        <VerifyEmailForm signedIn={Boolean(user)} />
        {user && <Link href="/account" className="mt-6 inline-block text-sm text-teal-700 underline dark:text-teal-300">返回帳號頁／重新寄信</Link>}
      </section>
    </main>
  );
}
