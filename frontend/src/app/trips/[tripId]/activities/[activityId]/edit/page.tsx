import Link from "next/link";
import { getTrip } from "@/lib/trips";
import { getActivity } from "@/lib/collaboration";
import ActivityForm from "../../../../activity-form";
import { saveActivity } from "../../../../activity-actions";

export default async function EditActivityPage({
  params,
}: {
  params: Promise<{ tripId: string; activityId: string }>;
}) {
  const { tripId, activityId } = await params;
  const trip = await getTrip(tripId);
  const activity = await getActivity(tripId, activityId);
  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href={`/trips/${trip.id}?day=${activity.activity_date}`}
        className="text-sm text-zinc-500 hover:underline"
      >
        ← 返回每日行程
      </Link>
      <h1 className="mb-8 mt-6 text-3xl font-bold">編輯活動</h1>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <ActivityForm
          trip={trip}
          day={activity.activity_date}
          activity={activity}
          saveAction={saveActivity.bind(null, trip.id, activity.id)}
        />
      </section>
    </div>
  );
}
