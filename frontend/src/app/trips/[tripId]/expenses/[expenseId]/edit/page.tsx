import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip, isTripId } from "@/lib/trips";
import { getLedger } from "@/lib/expenses";
import { getActivities } from "@/lib/collaboration";
import { localToday } from "@/lib/money";
import TripHeader from "../../../../trip-header";
import ExpenseForm from "../../../../expense-form";
import { saveExpense } from "../../../../expense-actions";

export const metadata: Metadata = { title: "編輯費用 | TripSync" };
export default async function EditExpensePage({
  params,
}: {
  params: Promise<{ tripId: string; expenseId: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId, expenseId } = await params;
  if (!isTripId(expenseId)) notFound();
  const trip = await getTrip(tripId);
  const [ledger, activities] = await Promise.all([
    getLedger(tripId),
    getActivities(tripId),
  ]);
  const expense = ledger.expenses.find((item) => item.id === Number(expenseId));
  if (!expense || (expense.created_by !== user.id && trip.owner_id !== user.id))
    notFound();
  const historical = new Set([
    expense.payer_id,
    ...expense.shares.map((share) => share.user_id),
  ]);
  return (
    <>
      <TripHeader trip={trip} active="expenses" />
      <section className="mx-auto max-w-2xl rounded-2xl border border-zinc-200 bg-white p-5 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="mb-6 text-2xl font-bold">編輯旅行費用</h2>
        <ExpenseForm
          trip={trip}
          people={ledger.balances.filter(
            (person) => person.active || historical.has(person.user_id),
          )}
          activities={activities}
          digits={ledger.minor_digits}
          today={localToday(trip.timezone)}
          expense={expense}
          saveAction={saveExpense.bind(null, trip.id, expense.id)}
        />
      </section>
    </>
  );
}
