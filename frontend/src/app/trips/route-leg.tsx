"use client";

import { useState, useTransition } from "react";
import type { Activity, Trip } from "@/lib/trip-types";
import type { RouteResult } from "@/lib/planner-types";
import { queryRoute } from "./planner-actions";

export default function RouteLeg({
  trip,
  day,
  origin,
  destination,
  onRoute,
}: {
  trip: Trip;
  day: string;
  origin: Activity;
  destination: Activity;
  onRoute: (id: string, line: string) => void;
}) {
  const [mode, setMode] = useState("TRANSIT");
  const [departure, setDeparture] = useState(
    origin.activity_date === day
      ? (origin.end_time?.slice(0, 5) ?? "09:00")
      : "09:00",
  );
  const [route, setRoute] = useState<RouteResult>();
  const [error, setError] = useState("");
  const [pending, startTransition] = useTransition();
  const routeId = `${origin.id}-${destination.id}`;
  function clear() {
    setRoute(undefined);
    setError("");
    onRoute(routeId, "");
  }
  const navigation = new URL("https://www.google.com/maps/dir/");
  navigation.search = new URLSearchParams({
    api: "1",
    origin: origin.title,
    destination: destination.title,
    ...(origin.place_id ? { origin_place_id: origin.place_id } : {}),
    ...(destination.place_id
      ? { destination_place_id: destination.place_id }
      : {}),
    travelmode:
      mode === "TRANSIT" ? "transit" : mode === "DRIVE" ? "driving" : "walking",
  }).toString();
  return (
    <article className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <p className="text-sm font-medium">
        {origin.title} → {destination.title}
      </p>
      {!origin.place_id || !destination.place_id ? (
        <p className="mt-2 text-xs leading-6 text-zinc-500">
          兩個活動都連結地圖位置後，即可查詢交通時間。
        </p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <label className="text-xs text-zinc-500">
              交通方式
              <select
                aria-label={`${origin.title} 到 ${destination.title}的交通方式`}
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value);
                  clear();
                }}
                className="mt-1 block rounded-lg border border-zinc-300 bg-white p-2 text-sm text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              >
                <option value="TRANSIT">大眾運輸</option>
                <option value="WALK">步行</option>
                <option value="DRIVE">開車</option>
              </select>
            </label>
            <label className="text-xs text-zinc-500">
              出發時間
              <input
                aria-label={`${origin.title}出發時間`}
                type="time"
                required
                value={departure}
                onChange={(e) => {
                  setDeparture(e.target.value);
                  clear();
                }}
                className="mt-1 block rounded-lg border border-zinc-300 bg-white p-2 text-sm text-zinc-800 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
              />
            </label>
            <button
              type="button"
              disabled={pending || !departure}
              onClick={() =>
                startTransition(async () => {
                  const result = await queryRoute(trip.id, {
                    origin_id: origin.id,
                    destination_id: destination.id,
                    day,
                    mode,
                    departure_time: departure,
                  });
                  setError(result.error ?? "");
                  setRoute(result.route);
                  onRoute(routeId, result.route?.polyline ?? "");
                })
              }
              className="rounded-lg bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              {pending ? "查詢中…" : "查詢交通"}
            </button>
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            {day} · {trip.timezone}
            {mode === "DRIVE" ? " · 開車估時未納入即時路況" : ""}
          </p>
        </>
      )}
      <div aria-live="polite">
        {error && (
          <p
            role="alert"
            className="mt-3 text-sm text-red-700 dark:text-red-300"
          >
            {error}
          </p>
        )}
        {route?.status === "ok" && (
          <div className="mt-3 text-sm">
            <p className="font-semibold text-teal-800 dark:text-teal-300">
              約 {route.minutes} 分鐘 ·{" "}
              {((route.distance_meters ?? 0) / 1000).toFixed(1)} 公里
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              預計抵達{" "}
              {route.arrival_at &&
                new Intl.DateTimeFormat("zh-TW", {
                  timeZone: trip.timezone,
                  month: "numeric",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: false,
                }).format(new Date(route.arrival_at))}
            </p>
            {route.time_conflict && (
              <p className="mt-2 font-medium text-amber-800 dark:text-amber-300">
                時間可能不足，預計抵達已晚於下一活動開始時間。
              </p>
            )}
            {route.steps?.map((step, index) => (
              <p key={index} className="mt-2 text-xs text-zinc-500">
                {step.line}：{step.from} → {step.to}
              </p>
            ))}
            <p className="mt-2 text-xs text-zinc-500">
              Google Maps · 查詢於{" "}
              {route.queried_at &&
                new Intl.DateTimeFormat("zh-TW", {
                  timeZone: trip.timezone,
                  hour: "2-digit",
                  minute: "2-digit",
                }).format(new Date(route.queried_at))}
              ，班次與交通時間可能變動。
            </p>
          </div>
        )}
        {route && route.status !== "ok" && (
          <p className="mt-3 text-sm text-amber-800 dark:text-amber-300">
            {route.message}
          </p>
        )}
      </div>
      <a
        href={navigation.toString()}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 inline-block text-xs text-teal-700 underline dark:text-teal-300"
      >
        在 Google Maps 查看路線 ↗
      </a>
    </article>
  );
}
