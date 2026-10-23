import Link from "next/link";
import { getTrip } from "@/lib/trips";
import { isTripDay } from "@/lib/trip-types";
import ActivityForm from "../../../activity-form";
import { saveActivity } from "../../../activity-actions";

export default async function NewActivityPage({
  params,
  searchParams,
}: {
  params: Promise<{ tripId: string }>;
  searchParams: Promise<{ day?: string }>;
}) {
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const { day: requested } = await searchParams;
  const day = isTripDay(requested, trip) ? requested : trip.start_date;
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href={`/trips/${trip.id}?day=${day}`}
        className="text-sm text-zinc-500 hover:underline"
      >
        ← 返回每日行程
      </Link>
      <h1 className="mt-6 text-3xl font-bold">新增活動</h1>
      <p className="mb-8 mt-3 text-sm text-zinc-500">
        {trip.name} · 把一天的安排，一件一件記下來。
      </p>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <ActivityForm
          trip={trip}
          day={day}
          saveAction={saveActivity.bind(null, trip.id, null)}
        />
      </section>
    </div>
  );
}
