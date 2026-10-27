"use client";
import Link from "next/link";
import { useActionState, useState } from "react";
import type { Activity, ActivityFormState, Trip } from "@/lib/trip-types";
import PlacePicker from "./place-picker";
import { categories } from "@/lib/planner-types";

const inputClass =
  "mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-4 py-3 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 dark:border-zinc-700";
export default function ActivityForm({
  trip,
  day,
  activity,
  saveAction,
}: {
  trip: Trip;
  day: string;
  activity?: Activity;
  saveAction: (
    state: ActivityFormState,
    form: FormData,
  ) => Promise<ActivityFormState>;
}) {
  const initial: ActivityFormState = {
    values: {
      title: activity?.title ?? "",
      activity_date: activity?.activity_date ?? day,
      start_time: activity?.start_time?.slice(0, 5) ?? "",
      end_time: activity?.end_time?.slice(0, 5) ?? "",
      location: activity?.location ?? "",
      notes: activity?.notes ?? "",
      place_id: activity?.place_id ?? "",
      category: activity?.category ?? "sight",
      stay_until: activity?.stay_until ?? "",
    },
  };
  const [state, action, pending] = useActionState(saveAction, initial);
  const [category, setCategory] = useState(initial.values.category);
  const fields = [
    {
      name: "title" as const,
      label: "活動名稱",
      type: "text",
      required: true,
      maxLength: 100,
      placeholder: "例如：上午逛小樽運河",
    },
    {
      name: "activity_date" as const,
      label: "日期",
      type: "date",
      required: true,
      min: trip.start_date,
      max: trip.end_date,
    },
    { name: "start_time" as const, label: "開始時間（選填）", type: "time" },
    { name: "end_time" as const, label: "結束時間（選填）", type: "time" },
    {
      name: "location" as const,
      label: "地點說明（選填）",
      type: "text",
      maxLength: 200,
      placeholder: "例如：在車站東出口集合…",
    },
  ];
  return (
    <form action={action} className="space-y-6">
      <label className="block text-sm font-medium">
        地點類型
        <select
          name="category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className={inputClass}
        >
          {Object.entries(categories).map(([value, item]) => (
            <option key={value} value={value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>
      <PlacePicker
        key={`${state.values.place_id}-${state.error ?? ""}`}
        tripId={trip.id}
        initialId={state.values.place_id}
      />
      <div className="grid gap-6 sm:grid-cols-2">
        {fields.map((field) => (
          <div
            key={field.name}
            className={
              field.name === "title" || field.name === "location"
                ? "sm:col-span-2"
                : undefined
            }
          >
            <label htmlFor={field.name} className="text-sm font-medium">
              {field.label}
            </label>
            <input
              {...field}
              id={field.name}
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
      {category === "lodging" && (
        <label className="block text-sm font-medium">
          退房日期（選填）
          <input
            name="stay_until"
            type="date"
            min={trip.start_date}
            max={trip.end_date}
            defaultValue={state.values.stay_until}
            className={inputClass}
          />
          <span className="mt-2 block text-xs font-normal text-zinc-500">
            活動日期為入住日；住宿也會出現在入住日至退房日的地圖上。
          </span>
        </label>
      )}
      <p className="text-xs leading-6 text-zinc-500">
        時間以 {trip.timezone}{" "}
        當地時間記錄，交通查詢會依此換算。暫未決定時可留白，跨夜活動請分別記在兩天。
      </p>
      <div>
        <label htmlFor="notes" className="text-sm font-medium">
          備註（選填）
        </label>
        <textarea
          id="notes"
          name="notes"
          maxLength={2000}
          rows={4}
          defaultValue={state.values.notes}
          className={inputClass}
          placeholder="集合方式、預約資訊或想提醒旅伴的事…"
        />
      </div>
      <div aria-live="polite">
        {state.error && (
          <p
            role="alert"
            className="rounded-xl bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300"
          >
            {state.error}
          </p>
        )}
      </div>
      <div className="flex flex-wrap gap-4">
        <button
          disabled={pending}
          className="rounded-xl bg-teal-700 px-6 py-3 text-sm font-semibold text-white disabled:opacity-50"
        >
          {pending ? "儲存中…" : activity ? "儲存活動" : "加入每日行程"}
        </button>
        <Link
          href={`/trips/${trip.id}?day=${day}`}
          className="px-4 py-3 text-sm hover:underline"
        >
          取消
        </Link>
      </div>
    </form>
  );
}
