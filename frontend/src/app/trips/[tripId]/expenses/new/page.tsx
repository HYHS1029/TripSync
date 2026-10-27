import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip } from "@/lib/trips";
import { getLedger } from "@/lib/expenses";
import { getActivities } from "@/lib/collaboration";
import { localToday } from "@/lib/money";
import TripHeader from "../../../trip-header";
import ExpenseForm from "../../../expense-form";
import { saveExpense } from "../../../expense-actions";

export const metadata: Metadata = { title: "新增費用 | TripSync" };
export default async function NewExpensePage({
  params,
  searchParams,
}: {
  params: Promise<{ tripId: string }>;
  searchParams: Promise<{ activity?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const [ledger, activities, query] = await Promise.all([
    getLedger(tripId),
    getActivities(tripId),
    searchParams,
  ]);
  return (
    <>
      <TripHeader trip={trip} active="expenses" />
      <section className="mx-auto max-w-2xl rounded-2xl border border-zinc-200 bg-white p-5 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="mb-6 text-2xl font-bold">記一筆旅行費用</h2>
        <ExpenseForm
          trip={trip}
          people={ledger.balances.filter((person) => person.active)}
          activities={activities}
          digits={ledger.minor_digits}
          today={localToday(trip.timezone)}
          activityId={Number(query.activity)}
          defaultPayerId={user.id}
          saveAction={saveExpense.bind(null, trip.id, null)}
        />
      </section>
    </>
  );
}
