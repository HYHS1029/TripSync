import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { logout } from "@/app/login/actions";

export const metadata: Metadata = { title: "我的帳號 | TripSync" };

export default async function AccountPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");

  const joinedAt = new Intl.DateTimeFormat("zh-TW", {
    dateStyle: "long",
    timeZone: "Asia/Taipei",
  }).format(new Date(user.created_at));

  return (
    <main className="min-h-screen bg-zinc-50 px-6 py-12 dark:bg-zinc-950">
      <div className="mx-auto max-w-2xl">
        <nav className="mb-12 flex items-center justify-between" aria-label="帳號導覽">
          <Link href="/" className="text-lg font-bold text-teal-700 dark:text-teal-400">
            TripSync
          </Link>
          <form action={logout}>
            <button className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800">
              登出
            </button>
          </form>
        </nav>
        <p className="mb-2 text-sm font-medium text-teal-700 dark:text-teal-400">我的帳號</p>
        <h1 className="text-3xl font-bold tracking-tight">你好，{user.username}</h1>
        <p className="mt-3 text-zinc-600 dark:text-zinc-400">歡迎回到 TripSync。</p>
        <section className="mt-8 rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900" aria-labelledby="account-details">
          <h2 id="account-details" className="mb-6 text-lg font-semibold">帳號資料</h2>
          <dl className="space-y-5">
            <div>
              <dt className="text-sm text-zinc-500 dark:text-zinc-400">使用者名稱</dt>
              <dd className="mt-1 break-words font-medium">{user.username}</dd>
            </div>
            <div>
              <dt className="text-sm text-zinc-500 dark:text-zinc-400">電子郵件</dt>
              <dd className="mt-1 break-all font-medium">{user.email}</dd>
            </div>
            <div>
              <dt className="text-sm text-zinc-500 dark:text-zinc-400">加入日期</dt>
              <dd className="mt-1 font-medium">{joinedAt}</dd>
            </div>
          </dl>
        </section>
      </div>
    </main>
  );
}
