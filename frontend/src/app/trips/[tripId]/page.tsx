import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip } from "@/lib/trips";
import { getActivities, getMembers } from "@/lib/collaboration";
import { addDays, formatTripDate, isTripDay, tripDays } from "@/lib/trip-types";
import DeleteTripForm from "../delete-trip-form";
import TripHeader from "../trip-header";
import ConfirmAction from "../confirm-action";
import { deleteActivity } from "../activity-actions";
import { deleteTrip } from "../actions";

export const metadata: Metadata = { title: "每日行程 | TripSync" };

export default async function TripPage({
  params,
  searchParams,
}: {
  params: Promise<{ tripId: string }>;
  searchParams: Promise<{ day?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const { day: requested } = await searchParams;
  const day = isTripDay(requested, trip) ? requested : trip.start_date;
  const [activities, members] = await Promise.all([
    getActivities(tripId),
    getMembers(tripId),
  ]);
  const dayIndex = Math.round(
    (Date.parse(day) - Date.parse(trip.start_date)) / 86_400_000,
  );
  const weekStart = Math.floor(dayIndex / 7) * 7;
  const days = Array.from(
    { length: Math.min(7, tripDays(trip) - weekStart) },
    (_, index) => addDays(trip.start_date, weekStart + index),
  );
  const counts = new Map<string, number>();
  for (const activity of activities)
    counts.set(
      activity.activity_date,
      (counts.get(activity.activity_date) ?? 0) + 1,
    );
  const today = activities.filter((activity) => activity.activity_date === day);
  const owner = trip.owner_id === user.id;
  const newPath = `/trips/${trip.id}/activities/new?day=${day}`;

  return (
    <>
      <TripHeader trip={trip} active="itinerary" />
      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_280px]">
        <section aria-labelledby="daily-heading" className="min-w-0">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 id="daily-heading" className="text-2xl font-bold">
                每天，都有新的期待
              </h2>
              <p className="mt-2 text-sm text-zinc-500">
                {activities.length} 個活動 · {members.length} 位旅伴一起規劃
              </p>
            </div>
            <Link
              href={newPath}
              className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-800"
            >
              ＋ 新增活動
            </Link>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-5 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-teal-700 dark:text-teal-300">
                  DAY {dayIndex + 1}
                </p>
                <h3 className="mt-1 font-semibold">{formatTripDate(day)}</h3>
              </div>
              <form method="get" className="flex items-end gap-2">
                <div>
                  <label
                    htmlFor="itinerary-day"
                    className="block text-xs text-zinc-500"
                  >
                    跳至日期
                  </label>
                  <input
                    id="itinerary-day"
                    name="day"
                    type="date"
                    min={trip.start_date}
                    max={trip.end_date}
                    defaultValue={day}
                    className="mt-1 max-w-40 rounded-lg border border-zinc-200 bg-transparent px-2 py-2 text-sm dark:border-zinc-700"
                  />
                </div>
                <button className="rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700">
                  查看
                </button>
              </form>
            </div>
            <nav
              aria-label="每日日期"
              className="grid grid-cols-4 gap-2 sm:grid-cols-7"
            >
              {days.map((date, index) => (
                <Link
                  key={date}
                  href={`/trips/${trip.id}?day=${date}`}
                  aria-current={date === day ? "date" : undefined}
                  className={`rounded-xl px-2 py-3 text-center text-sm ${date === day ? "bg-teal-700 text-white" : "bg-zinc-50 text-zinc-600 hover:bg-teal-50 dark:bg-zinc-800 dark:text-zinc-300"}`}
                >
                  <span className="block text-xs opacity-80">
                    Day {weekStart + index + 1}
                  </span>
                  <span className="mt-1 block font-semibold">
                    {date.slice(5).replace("-", "/")}
                  </span>
                  <span className="mt-1 block text-xs opacity-80">
                    {counts.get(date) ?? 0} 個活動
                  </span>
                </Link>
              ))}
            </nav>
            <div className="mt-3 flex justify-between text-xs text-zinc-500">
              {weekStart > 0 ? (
                <Link
                  href={`/trips/${trip.id}?day=${addDays(trip.start_date, weekStart - 7)}`}
                  className="py-2 hover:underline"
                >
                  ← 前七天
                </Link>
              ) : (
                <span />
              )}
              {weekStart + 7 < tripDays(trip) && (
                <Link
                  href={`/trips/${trip.id}?day=${addDays(trip.start_date, weekStart + 7)}`}
                  className="py-2 hover:underline"
                >
                  後七天 →
                </Link>
              )}
            </div>
          </div>
          {today.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-dashed border-zinc-300 px-6 py-14 text-center dark:border-zinc-700">
              <p className="text-3xl" aria-hidden="true">
                ☀
              </p>
              <h3 className="mt-4 text-lg font-semibold">
                這一天，還有很多可能
              </h3>
              <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-zinc-500">
                加上想去的景點、想吃的餐廳，或留一段自由探索的時間。
              </p>
              <Link
                href={newPath}
                className="mt-6 inline-block rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white"
              >
                安排第一個活動
              </Link>
            </div>
          ) : (
            <ol className="mt-6 space-y-4">
              {today.map((activity) => (
                <li key={activity.id} className="flex gap-3 sm:gap-5">
                  <div className="w-14 shrink-0 pt-5 text-right text-sm font-semibold text-teal-800 dark:text-teal-300">
                    {activity.start_time?.slice(0, 5) ?? "未定"}
                    {activity.end_time && (
                      <span className="mt-1 block text-xs font-normal text-zinc-500">
                        至 {activity.end_time.slice(0, 5)}
                      </span>
                    )}
                  </div>
                  <article className="min-w-0 flex-1 rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
                    <h3 className="break-words text-lg font-bold">
                      {activity.title}
                    </h3>
                    {activity.location && (
                      <p className="mt-2 break-words text-sm text-teal-800 dark:text-teal-300">
                        ⌖ {activity.location}
                      </p>
                    )}
                    {activity.notes && (
                      <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-zinc-600 dark:text-zinc-400">
                        {activity.notes}
                      </p>
                    )}
                    <div className="mt-4 flex flex-wrap items-start gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
                      <Link
                        href={`/trips/${trip.id}/activities/${activity.id}/edit`}
                        className="rounded-lg px-3 py-2 text-sm text-zinc-600 hover:bg-zinc-50 dark:text-zinc-300 dark:hover:bg-zinc-800"
                      >
                        編輯活動
                      </Link>
                      <ConfirmAction
                        action={deleteActivity.bind(
                          null,
                          trip.id,
                          activity.id,
                          day,
                        )}
                        label="刪除活動"
                        confirmation={`確定刪除「${activity.title}」？這項操作無法復原。`}
                      />
                    </div>
                  </article>
                </li>
              ))}
            </ol>
          )}
        </section>
        <aside className="space-y-5">
          <section className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="font-semibold">旅程筆記</h2>
            <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 text-zinc-600 dark:text-zinc-400">
              {trip.description || "還沒有旅程說明"}
            </p>
            {owner && (
              <Link
                href={`/trips/${trip.id}/edit`}
                className="mt-4 inline-block text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
              >
                編輯旅程資料 →
              </Link>
            )}
          </section>
          <section className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="font-semibold">和旅伴一起安排</h2>
            <p className="mt-3 text-sm leading-7 text-zinc-500">
              目前有 {members.length} 位旅伴，共同編輯這份每日行程。
            </p>
            <Link
              href={`/trips/${trip.id}/members`}
              className="mt-4 inline-block text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
            >
              {owner ? "管理旅伴與邀請 →" : "查看旅伴 →"}
            </Link>
          </section>
          {owner && (
            <section className="rounded-2xl border border-zinc-200 p-5 dark:border-zinc-800">
              <h2 className="mb-3 text-sm font-semibold text-zinc-500">
                旅程管理
              </h2>
              <DeleteTripForm
                deleteAction={deleteTrip.bind(null, trip.id)}
                name={trip.name}
              />
            </section>
          )}
        </aside>
      </div>
    </>
  );
}
