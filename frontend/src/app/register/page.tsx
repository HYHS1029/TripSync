import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import RegisterForm from "./register-form";

export const metadata: Metadata = { title: "註冊 | TripSync" };

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const returnToJoin = (await searchParams).next === "join";
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
          <h1 className="text-3xl font-bold tracking-tight">建立你的帳號</h1>
          <p className="mb-8 mt-3 text-sm leading-6 text-zinc-600 dark:text-zinc-400">
            為下一趟旅行，留下一起出發的位置。
          </p>
          {returnToJoin && (
            <p className="mb-4 text-sm text-teal-700 dark:text-teal-300">
              完成註冊與登入後，會回到旅程邀請。
            </p>
          )}
          <RegisterForm returnToJoin={returnToJoin} />
          <p className="mt-6 text-center text-sm text-zinc-600 dark:text-zinc-400">
            已經有帳號？{" "}
            <Link
              href={returnToJoin ? "/login?next=join" : "/login"}
              className="font-medium text-teal-700 underline-offset-4 hover:underline dark:text-teal-400"
            >
              登入
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
