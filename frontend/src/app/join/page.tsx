import type { Metadata } from "next";
import Link from "next/link";
import { getCurrentUser } from "@/lib/auth";
import JoinForm from "./join-form";

export const metadata: Metadata = {
  title: "加入旅程 | TripSync",
  robots: { index: false, follow: false },
};

export default async function JoinPage() {
  const user = await getCurrentUser().catch(() => null);
  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6 py-12 dark:bg-zinc-950">
      <section className="w-full max-w-md rounded-3xl border border-zinc-200 bg-white p-7 shadow-sm sm:p-9 dark:border-zinc-800 dark:bg-zinc-900">
        <Link href="/" className="font-bold text-teal-700 dark:text-teal-300">
          TripSync
        </Link>
        <p className="mt-8 text-sm font-medium text-teal-700 dark:text-teal-300">
          好旅程，和對的人一起
        </p>
        <h1 className="mt-3 text-3xl font-bold">你收到了一份旅程邀請</h1>
        <p className="mt-4 text-sm leading-7 text-zinc-600 dark:text-zinc-400">
          {user
            ? `目前以 ${user.username} 登入。確認後即可查看旅程，並和旅伴一起安排每日行程。`
            : "先登入或建立帳號，再回到這裡確認加入。我們會替你保留邀請 15 分鐘。"}
        </p>
        <JoinForm signedIn={Boolean(user)} />
        <p className="mt-5 text-xs leading-6 text-zinc-500">
          請確認這份邀請來自你信任的人。單純開啟此頁不會自動加入旅程。
        </p>
      </section>
    </main>
  );
}
