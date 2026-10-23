import type { Metadata } from "next";
import Link from "next/link";
import TripForm from "../trip-form";
import { createTrip } from "../actions";

export const metadata: Metadata = { title: "建立旅程 | TripSync" };

export default function NewTripPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/trips"
        className="text-sm text-zinc-500 underline-offset-4 hover:underline"
      >
        ← 返回我的旅程
      </Link>
      <h1 className="mt-6 text-3xl font-bold tracking-tight">建立旅程</h1>
      <p className="mb-8 mt-3 text-zinc-600 dark:text-zinc-400">
        先記下目的地和日期，讓計畫有個開始。
      </p>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <TripForm saveAction={createTrip} />
      </section>
    </div>
  );
}
