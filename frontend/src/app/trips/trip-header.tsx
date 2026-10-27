import Link from "next/link";
import { formatTripDate, tripDays, type Trip } from "@/lib/trip-types";

export default function TripHeader({
  trip,
  active,
}: {
  trip: Trip;
  active: "itinerary" | "members" | "expenses";
}) {
  return (
    <>
      <Link
        href="/trips"
        className="text-sm text-zinc-500 underline-offset-4 hover:underline"
      >
        ← 我的旅程
      </Link>
      <header className="mt-6 rounded-3xl border border-teal-200 bg-teal-50/70 p-6 sm:p-8 dark:border-teal-900 dark:bg-teal-950/30">
        <p className="text-xs font-semibold tracking-widest text-teal-800 dark:text-teal-300">
          一起，把旅行安排好
        </p>
        <h1 className="mt-3 break-words text-3xl font-bold tracking-tight sm:text-4xl">
          {trip.name}
        </h1>
        <p className="mt-4 break-words text-lg text-zinc-700 dark:text-zinc-300">
          {trip.destination}
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-zinc-600 dark:text-zinc-400">
          <span>
            {formatTripDate(trip.start_date)} — {formatTripDate(trip.end_date)}
          </span>
          <span className="rounded-full bg-white px-3 py-1 font-medium text-teal-800 dark:bg-teal-950 dark:text-teal-200">
            {tripDays(trip)} 天
          </span>
          <span>私人旅程</span>
          <span>
            {trip.timezone} · {trip.currency}
          </span>
        </div>
      </header>
      <nav
        aria-label="旅程管理"
        className="mb-8 mt-6 flex gap-2 border-b border-zinc-200 dark:border-zinc-800"
      >
        {[
          { key: "itinerary", href: `/trips/${trip.id}`, label: "每日行程" },
          {
            key: "expenses",
            href: `/trips/${trip.id}/expenses`,
            label: "記帳與分帳",
          },
          {
            key: "members",
            href: `/trips/${trip.id}/members`,
            label: "旅伴與邀請",
          },
        ].map((item) => (
          <Link
            key={item.key}
            href={item.href}
            aria-current={active === item.key ? "page" : undefined}
            className={`border-b-2 px-4 py-3 text-sm font-semibold ${active === item.key ? "border-teal-700 text-teal-800 dark:text-teal-300" : "border-transparent text-zinc-500 hover:text-teal-700"}`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </>
  );
}
