import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser, type CurrentUser } from "@/lib/auth";
import { logout } from "@/app/login/actions";

export default async function TripsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let user: CurrentUser | null = null;
  let unavailable = false;
  try {
    user = await getCurrentUser();
  } catch {
    unavailable = true;
  }
  if (!unavailable && !user) redirect("/login");

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <nav
          aria-label="主要導覽"
          className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-6 py-5"
        >
          <Link
            href="/"
            className="mr-auto text-xl font-bold text-teal-700 dark:text-teal-400"
          >
            TripSync
          </Link>
          <Link
            href="/trips"
            className="text-sm font-medium hover:text-teal-700"
          >
            我的旅程
          </Link>
          <Link
            href="/account"
            className="max-w-40 truncate text-sm text-zinc-600 dark:text-zinc-400"
          >
            {user?.username ?? "我的帳號"}
          </Link>
          <form action={logout}>
            <button className="text-sm underline-offset-4 hover:underline">
              登出
            </button>
          </form>
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
        {unavailable ? (
          <section className="py-16 text-center">
            <h1 className="text-2xl font-bold">暫時無法載入旅程</h1>
            <p className="mb-6 mt-3 text-zinc-600 dark:text-zinc-400">
              目前無法連線，請稍後重試。
            </p>
            <form action="/trips" method="get">
              <button className="rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white">
                重新載入
              </button>
            </form>
          </section>
        ) : (
          children
        )}
      </main>
    </div>
  );
}
