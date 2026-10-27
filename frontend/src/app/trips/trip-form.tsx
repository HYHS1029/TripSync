"use client";

import Link from "next/link";
import { useActionState } from "react";
import type { Trip, TripValues, TripFormState } from "@/lib/trip-types";

const fields: {
  name: keyof Pick<
    TripValues,
    "name" | "destination" | "start_date" | "end_date"
  >;
  label: string;
  type: string;
  maxLength?: number;
  placeholder?: string;
}[] = [
  {
    name: "name",
    label: "旅程名稱",
    type: "text",
    maxLength: 100,
    placeholder: "例如：北海道滑雪之旅",
  },
  {
    name: "destination",
    label: "目的地",
    type: "text",
    maxLength: 200,
    placeholder: "例如：日本・北海道",
  },
  { name: "start_date", label: "出發日期", type: "date" },
  { name: "end_date", label: "結束日期", type: "date" },
];

export default function TripForm({
  trip,
  saveAction,
}: {
  trip?: Trip;
  saveAction: (state: TripFormState, form: FormData) => Promise<TripFormState>;
}) {
  const [state, action, pending] = useActionState(saveAction, {
    values: {
      name: trip?.name ?? "",
      destination: trip?.destination ?? "",
      start_date: trip?.start_date ?? "",
      end_date: trip?.end_date ?? "",
      description: trip?.description ?? "",
      timezone: trip?.timezone ?? "Asia/Taipei",
      currency: trip?.currency ?? "TWD",
    },
  });
  const inputClass =
    "mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 dark:border-zinc-700";

  return (
    <form action={action} className="space-y-6">
      <div className="grid gap-6 sm:grid-cols-2">
        {fields.map((field) => (
          <div
            key={field.name}
            className={field.type === "date" ? "" : "sm:col-span-2"}
          >
            <label htmlFor={field.name} className="text-sm font-medium">
              {field.label}
            </label>
            <input
              id={field.name}
              name={field.name}
              type={field.type}
              required
              maxLength={field.maxLength}
              placeholder={field.placeholder}
              defaultValue={state.values[field.name]}
              className={inputClass}
              aria-invalid={Boolean(state.fieldErrors?.[field.name])}
              aria-describedby={
                state.fieldErrors?.[field.name]
                  ? `${field.name}-error`
                  : undefined
              }
            />
            {state.fieldErrors?.[field.name] && (
              <p
                id={`${field.name}-error`}
                className="mt-2 text-sm text-red-700 dark:text-red-300"
              >
                {state.fieldErrors[field.name]}
              </p>
            )}
          </div>
        ))}
      </div>
      <div className="grid gap-6 sm:grid-cols-2">
        <label className="text-sm font-medium">
          目的地時區
          <input
            name="timezone"
            required
            maxLength={64}
            list="trip-timezones"
            defaultValue={state.values.timezone}
            className={inputClass}
          />
          <datalist id="trip-timezones">
            {[
              "Asia/Taipei",
              "Asia/Tokyo",
              "Asia/Seoul",
              "Asia/Hong_Kong",
              "Asia/Shanghai",
              "Asia/Bangkok",
              "Asia/Singapore",
              "Europe/London",
              "Europe/Paris",
              "America/New_York",
              "America/Los_Angeles",
              "Australia/Sydney",
            ].map((zone) => (
              <option key={zone} value={zone} />
            ))}
          </datalist>
          <span className="mt-2 block text-xs font-normal text-zinc-500">
            交通查詢依當地時間計算，可輸入其他 IANA 時區。
          </span>
          {state.fieldErrors?.timezone && (
            <span className="block text-red-700">
              {state.fieldErrors.timezone}
            </span>
          )}
        </label>
        <label className="text-sm font-medium">
          記帳幣別
          <select
            name="currency"
            defaultValue={state.values.currency}
            className={inputClass}
          >
            {[
              "TWD",
              "JPY",
              "KRW",
              "USD",
              "EUR",
              "GBP",
              "HKD",
              "CNY",
              "THB",
              "SGD",
              "AUD",
              "CAD",
            ].map((currency) => (
              <option key={currency}>{currency}</option>
            ))}
          </select>
          <span className="mt-2 block text-xs font-normal text-zinc-500">
            每趟旅程先使用一種幣別；開始記帳後固定。
          </span>
        </label>
      </div>
      <div>
        <label htmlFor="description" className="text-sm font-medium">
          旅程說明 <span className="font-normal text-zinc-500">（選填）</span>
        </label>
        <textarea
          id="description"
          name="description"
          rows={4}
          maxLength={2000}
          defaultValue={state.values.description}
          className={inputClass}
          placeholder="記下這趟旅行的想法或注意事項…"
          aria-invalid={Boolean(state.fieldErrors?.description)}
          aria-describedby={
            state.fieldErrors?.description ? "description-error" : undefined
          }
        />
        {state.fieldErrors?.description && (
          <p
            id="description-error"
            className="mt-2 text-sm text-red-700 dark:text-red-300"
          >
            {state.fieldErrors.description}
          </p>
        )}
      </div>
      <div aria-live="polite" aria-atomic="true">
        {state.error && (
          <p
            role="alert"
            className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300"
          >
            {state.error}
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <button
          disabled={pending}
          className="rounded-xl bg-teal-700 px-6 py-3 font-semibold text-white hover:bg-teal-800 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-600 disabled:cursor-wait disabled:opacity-60"
        >
          {pending ? "儲存中…" : trip ? "儲存變更" : "建立旅程"}
        </button>
        <Link
          href={trip ? `/trips/${trip.id}` : "/trips"}
          className="rounded-xl px-4 py-3 text-sm font-medium underline-offset-4 hover:underline"
        >
          取消
        </Link>
      </div>
    </form>
  );
}
