import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip } from "@/lib/trips";
import { formatTripDate } from "@/lib/trip-types";
import DeleteTripForm from "../delete-trip-form";

export const metadata: Metadata = { title: "旅程詳情 | TripSync" };

export default async function TripPage({ params }: { params: Promise<{ tripId: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const isOwner = trip.owner_id === user.id;

  return (
    <div className="mx-auto max-w-3xl">
      <Link href="/trips" className="text-sm text-zinc-500 underline-offset-4 hover:underline">← 返回我的旅程</Link>
      <div className="mb-8 mt-8">
        <p className="mb-3 break-words text-sm font-medium text-teal-700 dark:text-teal-400">{trip.destination}</p>
        <h1 className="break-words text-3xl font-bold tracking-tight sm:text-4xl">{trip.name}</h1>
        <p className="mt-4 text-zinc-600 dark:text-zinc-400">{formatTripDate(trip.start_date)} 至 {formatTripDate(trip.end_date)}</p>
        <span className="mt-4 inline-block rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800 dark:bg-teal-950 dark:text-teal-300">{isOwner ? "你建立的旅程" : "你參與的旅程"}</span>
      </div>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="mb-4 text-lg font-semibold">旅程說明</h2>
        <p className="whitespace-pre-wrap break-words leading-7 text-zinc-600 dark:text-zinc-400">{trip.description || "還沒有旅程說明。"}</p>
      </section>
      {isOwner && (
        <div className="mt-6 flex flex-wrap items-start gap-4">
          <Link href={`/trips/${trip.id}/edit`} className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white hover:bg-teal-800">編輯旅程</Link>
          <DeleteTripForm tripId={trip.id} name={trip.name} />
        </div>
      )}
    </div>
  );
}
