"use client";

import Link from "next/link";
import { logout } from "@/app/login/actions";

export default function AccountError({ reset }: { reset: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <div className="max-w-md space-y-5 text-center">
        <h1 className="text-2xl font-bold">暫時無法載入帳號資料</h1>
        <p className="text-zinc-600 dark:text-zinc-400">請稍後再試，你也可以登出後重新登入。</p>
        <button onClick={reset} className="rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white">重試</button>
        <form action={logout}>
          <button className="text-sm underline underline-offset-4">登出</button>
        </form>
        <Link href="/" className="block text-sm underline underline-offset-4">返回首頁</Link>
      </div>
    </main>
  );
}
