import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip } from "@/lib/trips";
import TripForm from "../../trip-form";

export const metadata: Metadata = { title: "編輯旅程 | TripSync" };

export default async function EditTripPage({ params }: { params: Promise<{ tripId: string }> }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  if (trip.owner_id !== user.id) redirect(`/trips/${trip.id}`);

  return (
    <div className="mx-auto max-w-2xl">
      <Link href={`/trips/${trip.id}`} className="text-sm text-zinc-500 underline-offset-4 hover:underline">← 返回旅程詳情</Link>
      <h1 className="mt-6 text-3xl font-bold tracking-tight">編輯旅程</h1>
      <p className="mb-8 mt-3 text-zinc-600 dark:text-zinc-400">更新目的地、日期或旅程說明。</p>
      <section className="rounded-2xl border border-zinc-200 bg-white p-6 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900"><TripForm trip={trip} /></section>
    </div>
  );
}
