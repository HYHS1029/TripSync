import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/auth";
import { getTrip } from "@/lib/trips";
import { getLedger } from "@/lib/expenses";
import { getActivities } from "@/lib/collaboration";
import { expenseCategories } from "@/lib/expense-types";
import { amountInput, money } from "@/lib/money";
import TripHeader from "../../trip-header";
import ConfirmAction from "../../confirm-action";
import { deleteLedgerEntry } from "../../expense-actions";

export const metadata: Metadata = { title: "記帳與分帳 | TripSync" };
export default async function ExpensesPage({
  params,
  searchParams,
}: {
  params: Promise<{ tripId: string }>;
  searchParams: Promise<{ category?: string; date?: string }>;
}) {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  const { tripId } = await params;
  const trip = await getTrip(tripId);
  const [ledger, activities, filters] = await Promise.all([
    getLedger(tripId),
    getActivities(tripId),
    searchParams,
  ]);
  const format = (minor: number) =>
    money(minor, ledger.currency, ledger.minor_digits);
  const names = new Map(
    ledger.balances.map((person) => [person.user_id, person.username]),
  );
  const expenses = ledger.expenses.filter(
    (expense) =>
      (!filters.category || expense.category === filters.category) &&
      (!filters.date || expense.expense_date === filters.date),
  );
  const mine = ledger.balances.find((person) => person.user_id === user.id);
  return (
    <>
      <TripHeader trip={trip} active="expenses" />
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">一起旅行，帳也清楚</h2>
          <p className="mt-2 text-sm text-zinc-500">
            {ledger.expenses.length} 筆支出 · 付款與負擔分開記錄 ·{" "}
            {ledger.currency}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/trips/${trip.id}/settlements/new`}
            className="rounded-xl border border-zinc-300 px-4 py-3 text-sm font-semibold dark:border-zinc-700"
          >
            記錄還款
          </Link>
          <Link
            href={`/trips/${trip.id}/expenses/new`}
            className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white"
          >
            ＋ 記一筆費用
          </Link>
        </div>
      </div>
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        {[
          ["旅程總支出", format(ledger.total_minor)],
          ["我已代付", format(mine?.paid_minor ?? 0)],
          [
            (mine?.balance_minor ?? 0) >= 0 ? "我尚應收" : "我尚應付",
            format(Math.abs(mine?.balance_minor ?? 0)),
          ],
        ].map(([label, value]) => (
          <section
            key={label}
            className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <p className="text-sm text-zinc-500">{label}</p>
            <p className="mt-3 break-words text-2xl font-bold text-teal-800 dark:text-teal-300">
              {value}
            </p>
          </section>
        ))}
      </div>
      <div className="grid items-start gap-7 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="min-w-0" aria-label="費用明細">
          <form
            method="get"
            className="mb-5 flex flex-wrap items-end gap-3 rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
          >
            <label className="text-xs text-zinc-500">
              類別
              <select
                name="category"
                defaultValue={filters.category ?? ""}
                className="mt-1 block rounded-lg border border-zinc-300 bg-transparent p-2 text-sm dark:border-zinc-700"
              >
                <option value="">全部類別</option>
                {Object.entries(expenseCategories).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-zinc-500">
              日期
              <input
                name="date"
                type="date"
                defaultValue={filters.date ?? ""}
                className="mt-1 block rounded-lg border border-zinc-300 bg-transparent p-2 text-sm dark:border-zinc-700"
              />
            </label>
            <button className="rounded-lg bg-zinc-100 px-4 py-2 text-sm dark:bg-zinc-800">
              篩選
            </button>
            <Link
              href={`/trips/${trip.id}/expenses`}
              className="py-2 text-xs text-zinc-500 underline"
            >
              清除
            </Link>
          </form>
          {expenses.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-300 p-10 text-center dark:border-zinc-700">
              <h3 className="font-semibold">
                {ledger.expenses.length
                  ? "沒有符合條件的費用"
                  : "第一筆旅行開銷，從這裡開始"}
              </h3>
              <p className="mt-3 text-sm leading-7 text-zinc-500">
                住宿、餐費或車票，都能指定付款人與分攤旅伴。
              </p>
            </div>
          ) : (
            <ul className="space-y-4">
              {expenses.map((expense) => {
                const activity = activities.find(
                  (activity) => activity.id === expense.activity_id,
                );
                const editable =
                  expense.created_by === user.id || trip.owner_id === user.id;
                return (
                  <li
                    key={expense.id}
                    className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs text-zinc-500">
                          {expense.expense_date} ·{" "}
                          {expenseCategories[expense.category]}
                        </p>
                        <h3 className="mt-2 break-words text-lg font-bold">
                          {expense.title}
                        </h3>
                      </div>
                      <p className="text-lg font-bold">
                        {format(expense.amount_minor)}
                      </p>
                    </div>
                    <p className="mt-3 text-sm text-teal-800 dark:text-teal-300">
                      {names.get(expense.payer_id) ?? expense.payer_name} 先付款
                      · {expense.split_mode === "equal" ? "均分" : "自訂金額"}
                    </p>
                    <ul className="mt-3 flex flex-wrap gap-2">
                      {expense.shares.map((share) => (
                        <li
                          key={share.user_id}
                          className="rounded-lg bg-zinc-50 px-3 py-2 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
                        >
                          {names.get(share.user_id) ?? share.username} ·{" "}
                          {format(share.amount_minor)}
                        </li>
                      ))}
                    </ul>
                    {activity && (
                      <Link
                        href={`/trips/${trip.id}?day=${activity.activity_date}`}
                        className="mt-3 block text-xs text-teal-700 underline dark:text-teal-300"
                      >
                        關聯行程：{activity.title}
                      </Link>
                    )}
                    {expense.notes && (
                      <p className="mt-3 whitespace-pre-wrap break-words text-sm text-zinc-500">
                        {expense.notes}
                      </p>
                    )}
                    {editable && (
                      <div className="mt-4 flex flex-wrap items-start gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
                        <Link
                          href={`/trips/${trip.id}/expenses/${expense.id}/edit`}
                          className="rounded-lg px-3 py-2 text-sm text-zinc-500"
                        >
                          編輯費用
                        </Link>
                        <ConfirmAction
                          action={deleteLedgerEntry.bind(
                            null,
                            trip.id,
                            "expenses",
                            expense.id,
                          )}
                          label="刪除費用"
                          confirmation={`確定刪除「${expense.title}」？相關餘額會重新計算，已有還款紀錄會保留。`}
                        />
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          {ledger.settlements.length > 0 && (
            <section className="mt-8">
              <h3 className="mb-4 font-semibold">已記錄的還款</h3>
              <ul className="space-y-3">
                {ledger.settlements.map((settlement) => (
                  <li
                    key={settlement.id}
                    className="rounded-2xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <p className="text-xs text-zinc-500">
                      {settlement.settled_on}
                    </p>
                    <p className="mt-2 text-sm font-medium">
                      {names.get(settlement.sender_id) ??
                        settlement.sender_name}{" "}
                      →{" "}
                      {names.get(settlement.recipient_id) ??
                        settlement.recipient_name}{" "}
                      · {format(settlement.amount_minor)}
                    </p>
                    {settlement.notes && (
                      <p className="mt-2 whitespace-pre-wrap break-words text-sm text-zinc-500">
                        {settlement.notes}
                      </p>
                    )}
                    {(settlement.created_by === user.id ||
                      trip.owner_id === user.id) && (
                      <div className="mt-2">
                        <ConfirmAction
                          action={deleteLedgerEntry.bind(
                            null,
                            trip.id,
                            "settlements",
                            settlement.id,
                          )}
                          label="撤銷紀錄"
                          confirmation="確定撤銷這筆還款紀錄？應收與應付餘額會重新計算。"
                        />
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </section>
        <aside className="space-y-5">
          <section className="rounded-2xl border border-teal-200 bg-teal-50/60 p-5 dark:border-teal-900 dark:bg-teal-950/30">
            <h3 className="font-semibold">結算建議</h3>
            <p className="mt-2 text-xs leading-6 text-zinc-500">
              以下是沖抵後的待還款金額。實際完成付款後，再記錄還款。
            </p>
            {ledger.suggestions.length ? (
              <ul className="mt-4 space-y-4">
                {ledger.suggestions.map((transfer) => (
                  <li
                    key={`${transfer.sender_id}-${transfer.recipient_id}`}
                    className="rounded-xl bg-white p-4 dark:bg-zinc-900"
                  >
                    <p className="break-words text-sm">
                      {names.get(transfer.sender_id)} →{" "}
                      {names.get(transfer.recipient_id)}
                    </p>
                    <p className="mt-2 font-bold text-teal-800 dark:text-teal-300">
                      {format(transfer.amount_minor)}
                    </p>
                    <Link
                      href={`/trips/${trip.id}/settlements/new?sender=${transfer.sender_id}&recipient=${transfer.recipient_id}&amount=${amountInput(transfer.amount_minor, ledger.minor_digits)}`}
                      className="mt-3 inline-block text-xs font-semibold text-teal-700 underline dark:text-teal-300"
                    >
                      記錄已完成的還款 →
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm font-medium text-teal-800 dark:text-teal-300">
                {ledger.expenses.length
                  ? "目前已全部結清。"
                  : "新增費用後，這裡會顯示誰應還誰。"}
              </p>
            )}
          </section>
          <section className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
            <h3 className="font-semibold">每人帳務</h3>
            <ul className="mt-4 divide-y divide-zinc-100 dark:divide-zinc-800">
              {ledger.balances.map((person) => (
                <li key={person.user_id} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <p className="break-words font-semibold">
                      {person.username}
                      {!person.active && (
                        <span className="ml-1 text-xs font-normal text-zinc-500">
                          已離開
                        </span>
                      )}
                    </p>
                    <p
                      className={
                        person.balance_minor > 0
                          ? "text-teal-800 dark:text-teal-300"
                          : "text-zinc-600 dark:text-zinc-400"
                      }
                    >
                      {person.balance_minor === 0
                        ? "已結清"
                        : `${person.balance_minor > 0 ? "應收" : "應付"} ${format(Math.abs(person.balance_minor))}`}
                    </p>
                  </div>
                  <p className="mt-2 text-xs leading-6 text-zinc-500">
                    代付 {format(person.paid_minor)} · 負擔{" "}
                    {format(person.owed_minor)}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </>
  );
}
