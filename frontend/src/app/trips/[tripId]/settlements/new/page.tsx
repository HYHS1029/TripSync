import type { Metadata } from "next";
import Link from "next/link";
import { getTrip } from "@/lib/trips";
import { getLedger } from "@/lib/expenses";
import { localToday } from "@/lib/money";
import TripHeader from "../../../trip-header";
import SettlementForm from "../../../settlement-form";
import { saveSettlement } from "../../../expense-actions";

export const metadata: Metadata = { title: "記錄還款 | TripSync" };
export default async function NewSettlementPage({
  params,
  searchParams,
}: {
  params: Promise<{ tripId: string }>;
  searchParams: Promise<{
    sender?: string;
    recipient?: string;
    amount?: string;
  }>;
}) {
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const [ledger, query] = await Promise.all([getLedger(tripId), searchParams]);
  const validSender = ledger.balances.find(
    (person) =>
      person.user_id === Number(query.sender) && person.balance_minor < 0,
  );
  const validRecipient = ledger.balances.find(
    (person) =>
      person.user_id === Number(query.recipient) && person.balance_minor > 0,
  );
  return (
    <>
      <TripHeader trip={trip} active="expenses" />
      <section className="mx-auto max-w-2xl rounded-2xl border border-zinc-200 bg-white p-5 sm:p-8 dark:border-zinc-800 dark:bg-zinc-900">
        <h2 className="mb-6 text-2xl font-bold">記錄旅伴還款</h2>
        {ledger.suggestions.length ? (
          <SettlementForm
            trip={trip}
            ledger={ledger}
            initial={{
              sender_id: validSender ? String(validSender.user_id) : "",
              recipient_id: validRecipient
                ? String(validRecipient.user_id)
                : "",
              amount: query.amount?.slice(0, 20) ?? "",
              settled_on: localToday(trip.timezone),
              notes: "",
            }}
            saveAction={saveSettlement.bind(null, trip.id)}
          />
        ) : (
          <div>
            <p className="text-sm text-zinc-500">目前沒有待結清餘額。</p>
            <Link
              href={`/trips/${trip.id}/expenses`}
              className="mt-5 inline-block text-sm text-teal-700 underline"
            >
              返回記帳與分帳
            </Link>
          </div>
        )}
      </section>
    </>
  );
}
