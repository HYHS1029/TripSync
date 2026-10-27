"use client";

import Link from "next/link";
import { useActionState, useState } from "react";
import type { Activity, Trip } from "@/lib/trip-types";
import {
  expenseCategories,
  type Balance,
  type Expense,
  type ExpenseFormState,
} from "@/lib/expense-types";
import { amountInput, money, parseMinor } from "@/lib/money";

const inputClass =
  "mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 text-sm outline-none focus:border-teal-600 dark:border-zinc-700";
export default function ExpenseForm({
  trip,
  people,
  activities,
  digits,
  today,
  expense,
  activityId,
  defaultPayerId,
  saveAction,
}: {
  trip: Trip;
  people: Balance[];
  activities: Activity[];
  digits: number;
  today: string;
  expense?: Expense;
  activityId?: number;
  defaultPayerId?: number;
  saveAction: (
    state: ExpenseFormState,
    form: FormData,
  ) => Promise<ExpenseFormState>;
}) {
  const linked = activities.find(
    (activity) => activity.id === (expense?.activity_id ?? activityId),
  );
  const initial: ExpenseFormState = {
    values: {
      title: expense?.title ?? (linked ? `${linked.title}費用` : ""),
      expense_date: expense?.expense_date ?? today,
      category:
        expense?.category ??
        (linked?.category === "lodging"
          ? "lodging"
          : linked?.category === "station"
            ? "transport"
            : linked?.category === "food"
              ? "food"
              : "other"),
      amount: expense ? amountInput(expense.amount_minor, digits) : "",
      payer_id:
        expense?.payer_id.toString() ??
        defaultPayerId?.toString() ??
        people[0]?.user_id.toString() ??
        "",
      split_mode: expense?.split_mode ?? "equal",
      participant_ids:
        expense?.shares.map((share) => String(share.user_id)) ??
        people
          .filter((person) => person.active)
          .map((person) => String(person.user_id)),
      custom: Object.fromEntries(
        expense?.shares.map((share) => [
          String(share.user_id),
          amountInput(share.amount_minor, digits),
        ]) ?? [],
      ),
      activity_id: (expense?.activity_id ?? linked?.id)?.toString() ?? "",
      notes: expense?.notes ?? "",
    },
  };
  const [state, action, pending] = useActionState(saveAction, initial);
  const [amount, setAmount] = useState(initial.values.amount);
  const [mode, setMode] = useState(initial.values.split_mode);
  const [participants, setParticipants] = useState(
    initial.values.participant_ids,
  );
  const [custom, setCustom] = useState(initial.values.custom);
  const minor = parseMinor(amount, digits) ?? 0;
  const ordered = [...participants].sort((a, b) => Number(a) - Number(b));
  const quotient = participants.length
    ? Math.floor(minor / participants.length)
    : 0;
  const remainder = participants.length ? minor % participants.length : 0;
  const customTotal = participants.reduce(
    (sum, id) => sum + (parseMinor(custom[id] ?? "", digits) ?? 0),
    0,
  );
  return (
    <form action={action} className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <label className="text-sm font-medium sm:col-span-2">
          費用名稱
          <input
            name="title"
            required
            maxLength={100}
            defaultValue={state.values.title}
            className={inputClass}
            placeholder="例如：飯店住宿、晚餐、車票"
          />
        </label>
        <label className="text-sm font-medium">
          支出日期
          <input
            name="expense_date"
            type="date"
            required
            defaultValue={state.values.expense_date}
            className={inputClass}
          />
          <span className="mt-1 block text-xs font-normal text-zinc-500">
            可記錄出發前的預訂費用。
          </span>
        </label>
        <label className="text-sm font-medium">
          類別
          <select
            name="category"
            defaultValue={state.values.category}
            className={inputClass}
          >
            {Object.entries(expenseCategories).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium">
          金額（{trip.currency}）
          <input
            name="amount"
            inputMode="decimal"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={inputClass}
            placeholder={digits ? "0.00" : "0"}
          />
          <span className="mt-1 block text-xs font-normal text-zinc-500">
            {digits ? `最多 ${digits} 位小數` : "此幣別以整數記帳"}
          </span>
        </label>
        <label className="text-sm font-medium">
          誰先付款
          <select
            name="payer_id"
            defaultValue={state.values.payer_id}
            required
            className={inputClass}
          >
            {people.map((person) => (
              <option key={person.user_id} value={person.user_id}>
                {person.username}
                {person.active ? "" : "（已離開）"}
              </option>
            ))}
          </select>
        </label>
      </div>
      <section className="rounded-2xl border border-zinc-200 p-4 sm:p-5 dark:border-zinc-800">
        <h3 className="font-semibold">哪些人負擔這筆費用</h3>
        <p className="mt-2 text-xs leading-6 text-zinc-500">
          付款人可以不參與分攤。均分尾數依成員編號由小到大分配，總和會等於整筆費用。
        </p>
        <label className="mt-4 block text-sm">
          分攤方式
          <select
            name="split_mode"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className={inputClass}
          >
            <option value="equal">所選旅伴均分</option>
            <option value="custom">指定每人金額</option>
          </select>
        </label>
        <div className="mt-4 space-y-3">
          {people.map((person) => {
            const id = String(person.user_id),
              checked = participants.includes(id);
            return (
              <div
                key={id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-zinc-50 p-3 dark:bg-zinc-800"
              >
                <label className="flex items-center gap-3 text-sm">
                  <input
                    name="participant_ids"
                    type="checkbox"
                    value={id}
                    checked={checked}
                    onChange={(e) =>
                      setParticipants((current) =>
                        e.target.checked
                          ? [...current, id]
                          : current.filter((value) => value !== id),
                      )
                    }
                    className="h-4 w-4 accent-teal-700"
                  />
                  {person.username}
                  {!person.active && (
                    <span className="text-xs text-zinc-500">已離開</span>
                  )}
                </label>
                {checked &&
                  (mode === "custom" ? (
                    <label className="text-xs text-zinc-500">
                      分攤金額
                      <input
                        aria-label={`${person.username}分攤金額`}
                        name={`share_${id}`}
                        inputMode="decimal"
                        required
                        value={custom[id] ?? ""}
                        onChange={(e) =>
                          setCustom((current) => ({
                            ...current,
                            [id]: e.target.value,
                          }))
                        }
                        className="ml-2 w-28 rounded-lg border border-zinc-300 bg-white p-2 text-sm text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
                      />
                    </label>
                  ) : (
                    <span className="text-sm font-medium">
                      {money(
                        quotient + (ordered.indexOf(id) < remainder ? 1 : 0),
                        trip.currency,
                        digits,
                      )}
                    </span>
                  ))}
              </div>
            );
          })}
        </div>
        <p className="mt-4 text-sm text-zinc-500" aria-live="polite">
          {participants.length} 人分攤
          {mode === "custom"
            ? ` · 已分配 ${money(customTotal, trip.currency, digits)}，差額 ${money(minor - customTotal, trip.currency, digits)}`
            : ` · 合計 ${money(minor, trip.currency, digits)}`}
        </p>
      </section>
      <label className="block text-sm font-medium">
        關聯行程（選填）
        <select
          name="activity_id"
          defaultValue={state.values.activity_id}
          className={inputClass}
        >
          <option value="">獨立費用</option>
          {activities.map((activity) => (
            <option key={activity.id} value={activity.id}>
              {activity.activity_date} · {activity.title}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-medium">
        備註（選填）
        <textarea
          name="notes"
          rows={3}
          maxLength={2000}
          defaultValue={state.values.notes}
          className={inputClass}
        />
      </label>
      <div aria-live="polite">
        {state.error && (
          <p
            role="alert"
            className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300"
          >
            {state.error}
          </p>
        )}
      </div>
      <div className="flex gap-4">
        <button
          disabled={pending || !participants.length}
          className="rounded-xl bg-teal-700 px-6 py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          {pending ? "儲存中…" : expense ? "儲存費用" : "新增費用"}
        </button>
        <Link
          href={`/trips/${trip.id}/expenses`}
          className="px-4 py-3 text-sm hover:underline"
        >
          取消
        </Link>
      </div>
    </form>
  );
}
