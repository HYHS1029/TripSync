import type { Metadata } from "next";
import Link from "next/link";
import { getTrips } from "@/lib/trips";
import { formatTripDate } from "@/lib/trip-types";

export const metadata: Metadata = { title: "我的旅程 | TripSync" };

export default async function TripsPage() {
  const trips = await getTrips();
  return (
    <>
      <div className="mb-10 flex flex-wrap items-start justify-between gap-6">
        <div>
          <p className="mb-2 text-sm font-medium text-teal-700 dark:text-teal-400">下一站，一起出發</p>
          <h1 className="text-3xl font-bold tracking-tight">我的旅程</h1>
          <p className="mt-3 text-zinc-600 dark:text-zinc-400">把旅行的第一個想法，變成出發的計畫。</p>
        </div>
        <Link href="/trips/new" className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-800">建立旅程</Link>
      </div>
      {trips.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-zinc-300 px-6 py-16 text-center dark:border-zinc-700">
          <h2 className="text-xl font-semibold">第一趟旅程，從這裡開始</h2>
          <p className="mx-auto mb-7 mt-3 max-w-sm text-sm leading-6 text-zinc-600 dark:text-zinc-400">你還沒有參與的旅程。先決定目的地與日期，為下一次出發留個位置。</p>
          <Link href="/trips/new" className="inline-block rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-800">建立第一個旅程</Link>
        </section>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {trips.map((trip) => (
            <Link key={trip.id} href={`/trips/${trip.id}`} className="group flex flex-col rounded-2xl border border-zinc-200 bg-white p-6 transition-colors hover:border-teal-500 focus-visible:outline-2 focus-visible:outline-teal-600 dark:border-zinc-800 dark:bg-zinc-900">
              <p className="mb-4 break-words text-sm font-medium text-teal-700 dark:text-teal-400">{trip.destination}</p>
              <h2 className="break-words text-xl font-semibold group-hover:text-teal-700 dark:group-hover:text-teal-400">{trip.name}</h2>
              <p className="mt-3 text-sm leading-6 text-zinc-500 dark:text-zinc-400">{formatTripDate(trip.start_date)}<br />至 {formatTripDate(trip.end_date)}</p>
              {trip.description && <p className="mt-4 line-clamp-2 break-words text-sm leading-6 text-zinc-600 dark:text-zinc-400">{trip.description}</p>}
              <span className="mt-auto pt-6 text-sm font-medium">查看旅程 <span aria-hidden="true">→</span></span>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
