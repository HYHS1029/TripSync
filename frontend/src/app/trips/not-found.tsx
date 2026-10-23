import Link from "next/link";

export default function TripNotFound() {
  return (
    <section className="py-16 text-center">
      <h1 className="text-2xl font-bold">找不到這個旅程</h1>
      <p className="mb-6 mt-3 text-zinc-600 dark:text-zinc-400">
        旅程可能已被刪除，或你尚未加入。
      </p>
      <Link
        href="/trips"
        className="inline-block rounded-xl bg-teal-700 px-5 py-3 font-semibold text-white"
      >
        返回我的旅程
      </Link>
    </section>
  );
}
