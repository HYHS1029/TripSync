"use client";

import Link from "next/link";
import { useActionState } from "react";
import type {
  Ledger,
  SettlementFormState,
  SettlementValues,
} from "@/lib/expense-types";
import type { Trip } from "@/lib/trip-types";
import { money } from "@/lib/money";

const inputClass =
  "mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 text-sm dark:border-zinc-700";
export default function SettlementForm({
  trip,
  ledger,
  initial,
  saveAction,
}: {
  trip: Trip;
  ledger: Ledger;
  initial: SettlementValues;
  saveAction: (
    state: SettlementFormState,
    form: FormData,
  ) => Promise<SettlementFormState>;
}) {
  const [state, action, pending] = useActionState(saveAction, {
    values: initial,
  });
  return (
    <form action={action} className="space-y-6">
      <p className="rounded-xl bg-teal-50 p-4 text-sm leading-7 text-teal-900 dark:bg-teal-950/30 dark:text-teal-200">
        請在實際完成付款後記錄，可填入部分還款金額。這個操作會更新帳務餘額。
      </p>
      <div className="grid gap-5 sm:grid-cols-2">
        {[
          ["sender_id", "誰已還款", -1],
          ["recipient_id", "誰已收款", 1],
        ].map(([field, label, sign]) => (
          <label key={field} className="text-sm font-medium">
            {label}
            <select
              name={String(field)}
              required
              defaultValue={state.values[field as "sender_id" | "recipient_id"]}
              className={inputClass}
            >
              <option value="">請選擇旅伴</option>
              {ledger.balances
                .filter((person) => Number(sign) * person.balance_minor > 0)
                .map((person) => (
                  <option key={person.user_id} value={person.user_id}>
                    {person.username}
                    {person.active ? "" : "（已離開）"} ·{" "}
                    {money(
                      Math.abs(person.balance_minor),
                      ledger.currency,
                      ledger.minor_digits,
                    )}
                  </option>
                ))}
            </select>
          </label>
        ))}
      </div>
      <label className="block text-sm font-medium">
        已還金額（{ledger.currency}）
        <input
          name="amount"
          inputMode="decimal"
          required
          defaultValue={state.values.amount}
          className={inputClass}
        />
        <span className="mt-2 block text-xs font-normal text-zinc-500">
          金額不能超過雙方目前未結清餘額。
        </span>
      </label>
      <label className="block text-sm font-medium">
        還款日期
        <input
          name="settled_on"
          type="date"
          required
          defaultValue={state.values.settled_on}
          className={inputClass}
        />
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
          disabled={pending}
          className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          {pending ? "儲存中…" : "記錄已完成的還款"}
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
