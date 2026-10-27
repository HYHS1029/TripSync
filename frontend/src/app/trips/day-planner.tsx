"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, useTransition } from "react";
import type { Activity, Trip } from "@/lib/trip-types";
import { categories, type MapData } from "@/lib/planner-types";
import ConfirmAction from "./confirm-action";
import { deleteActivity } from "./activity-actions";
import { loadMapPoints, reorderActivities } from "./planner-actions";
import TripMap from "./trip-map";
import RouteLeg from "./route-leg";

export default function DayPlanner({
  trip,
  day,
  activities,
}: {
  trip: Trip;
  day: string;
  activities: Activity[];
}) {
  const router = useRouter();
  const today = activities.filter((item) => item.activity_date === day);
  const stays = activities.filter(
    (item) =>
      item.category === "lodging" &&
      item.activity_date <= day &&
      (item.stay_until ?? item.activity_date) >= day,
  );
  const inherited = stays.filter((item) => item.activity_date !== day);
  const [selected, setSelected] = useState<number | null>(null);
  const [view, setView] = useState("list");
  const [allDays, setAllDays] = useState(false);
  const [mapData, setMapData] = useState<MapData>({
    points: [],
    unavailable_ids: [],
    queried_at: "",
  });
  const [mapError, setMapError] = useState("");
  const [reload, setReload] = useState(0);
  const [loadingMap, startMapTransition] = useTransition();
  const [ordering, startOrderTransition] = useTransition();
  const [orderError, setOrderError] = useState("");
  const [hotelId, setHotelId] = useState(stays[0]?.id.toString() ?? "");
  const [endHotelId, setEndHotelId] = useState(
    stays.at(-1)?.id.toString() ?? "",
  );
  const [returnHotel, setReturnHotel] = useState(true);
  const [lines, setLines] = useState<Record<string, string>>({});
  const selectActivity = useCallback(
    (id: number) => {
      const point = mapData.points.find((point) => point.activity_id === id);
      if (point && !activities.some((activity) => activity.id === id)) {
        router.push(`/trips/${trip.id}?day=${point.day}`);
        return;
      }
      setSelected(id);
      document
        .getElementById(`activity-${id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    },
    [setSelected, mapData.points, activities, router, trip.id],
  );
  const onRoute = useCallback(
    (id: string, line: string) =>
      setLines((current) => ({ ...current, [id]: line })),
    [setLines],
  );
  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY) return;
    let active = true;
    startMapTransition(async () => {
      const result = await loadMapPoints(trip.id, day, allDays);
      if (active) {
        setMapData(
          result.data ?? { points: [], unavailable_ids: [], queried_at: "" },
        );
        setMapError(result.error ?? "");
      }
    });
    return () => {
      active = false;
    };
  }, [trip.id, day, allDays, reload]);
  const hotel = stays.find((stay) => String(stay.id) === hotelId);
  const endHotel = stays.find((stay) => String(stay.id) === endHotelId);
  const stops = today.filter((item) => item.category !== "lodging");
  const sequence = [
    ...(hotel ? [hotel] : []),
    ...stops,
    ...(endHotel && returnHotel && (stops.length || hotel?.id !== endHotel.id)
      ? [endHotel]
      : []),
  ];
  const legs = sequence
    .slice(1)
    .map((destination, index) => ({ origin: sequence[index], destination }))
    .filter((leg) => leg.origin.id !== leg.destination.id);
  const visibleLegs = new Set(
    legs.map((leg) => `${leg.origin.id}-${leg.destination.id}`),
  );
  function move(index: number, direction: number) {
    const ids = today.map((item) => item.id);
    [ids[index], ids[index + direction]] = [ids[index + direction], ids[index]];
    startOrderTransition(async () => {
      const result = await reorderActivities(trip.id, day, ids);
      setOrderError(result.error ?? "");
    });
  }
  const card = (activity: Activity, index: number, inheritedStay = false) => {
    const category = categories[activity.category] ?? categories.other;
    const point = mapData.points.find(
      (point) => point.activity_id === activity.id,
    );
    const focus = () => {
      setSelected(activity.id);
      if (activity.place_id) setView("map");
    };
    return (
      <li key={activity.id} id={`activity-${activity.id}`}>
        <article
          className={`rounded-2xl border bg-white p-5 dark:bg-zinc-900 ${selected === activity.id ? "border-teal-600 ring-2 ring-teal-600/20" : "border-zinc-200 dark:border-zinc-800"}`}
        >
          <div className="flex items-start gap-3">
            <button
              type="button"
              aria-label={`${activity.place_id ? "在地圖查看" : "選取"}${activity.title}`}
              onClick={focus}
              style={{ backgroundColor: category.color }}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-sm font-bold text-white"
            >
              {inheritedStay ? "宿" : index + 1}
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
                <span>{category.label}</span>
                <span>
                  {inheritedStay
                    ? "住宿期間"
                    : (activity.start_time?.slice(0, 5) ?? "時間未定")}
                  {!inheritedStay && activity.end_time
                    ? ` – ${activity.end_time.slice(0, 5)}`
                    : ""}
                </span>
              </div>
              <button
                type="button"
                onClick={focus}
                className="mt-1 break-words text-left text-lg font-bold"
              >
                {activity.title}
              </button>
              {point && (
                <p className="mt-2 text-xs text-teal-800 dark:text-teal-300">
                  ⌖ {point.name} · {point.address}
                </p>
              )}
              {activity.location && (
                <p className="mt-2 break-words text-sm text-zinc-500">
                  {activity.location}
                </p>
              )}
              {!activity.place_id && (
                <p className="mt-2 text-xs text-zinc-500">尚未連結地圖位置</p>
              )}
              {activity.stay_until && (
                <p className="mt-2 text-xs text-purple-700 dark:text-purple-300">
                  {activity.activity_date} 入住 · {activity.stay_until} 退房
                </p>
              )}
              {activity.notes && (
                <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-zinc-600 dark:text-zinc-400">
                  {activity.notes}
                </p>
              )}
            </div>
            {!inheritedStay && (
              <div className="flex shrink-0 flex-col gap-1">
                <button
                  aria-label={`上移${activity.title}`}
                  title="上移"
                  type="button"
                  disabled={ordering || index === 0}
                  onClick={() => move(index, -1)}
                  className="rounded-lg border border-zinc-200 px-2 py-1 disabled:opacity-25 dark:border-zinc-700"
                >
                  ↑
                </button>
                <button
                  aria-label={`下移${activity.title}`}
                  title="下移"
                  type="button"
                  disabled={ordering || index === today.length - 1}
                  onClick={() => move(index, 1)}
                  className="rounded-lg border border-zinc-200 px-2 py-1 disabled:opacity-25 dark:border-zinc-700"
                >
                  ↓
                </button>
              </div>
            )}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-zinc-100 pt-3 text-sm dark:border-zinc-800">
            <Link
              href={`/trips/${trip.id}/activities/${activity.id}/edit`}
              className="rounded-lg px-3 py-2 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-800"
            >
              編輯活動
            </Link>
            <Link
              href={`/trips/${trip.id}/expenses/new?activity=${activity.id}`}
              className="rounded-lg px-3 py-2 font-medium text-teal-700 dark:text-teal-300"
            >
              ＋ 記一筆費用
            </Link>
            <ConfirmAction
              action={deleteActivity.bind(null, trip.id, activity.id, day)}
              label="刪除活動"
              confirmation={`確定刪除「${activity.title}」？已記錄的費用會保留。`}
            />
          </div>
        </article>
      </li>
    );
  };
  return (
    <>
      <div className="mb-4 mt-5 flex gap-2 lg:hidden" aria-label="規劃視圖">
        {[
          ["list", "行程"],
          ["map", "地圖"],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={view === key}
            onClick={() => setView(key)}
            className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold ${view === key ? "bg-teal-700 text-white" : "border border-zinc-200 dark:border-zinc-800"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="mt-5 grid items-start gap-6 lg:grid-cols-2">
        <div
          className={`${view === "list" ? "block" : "hidden"} min-w-0 lg:block`}
        >
          {orderError && (
            <p
              role="alert"
              className="mb-4 text-sm text-red-700 dark:text-red-300"
            >
              {orderError}
            </p>
          )}
          {inherited.length > 0 && (
            <section className="mb-5">
              <h3 className="mb-3 text-sm font-semibold text-purple-700 dark:text-purple-300">
                當日住宿
              </h3>
              <ul className="space-y-3">
                {inherited.map((activity, index) =>
                  card(activity, index, true),
                )}
              </ul>
            </section>
          )}
          {today.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-300 px-5 py-12 text-center dark:border-zinc-700">
              <h3 className="font-semibold">這一天，還有很多可能</h3>
              <p className="mt-2 text-sm text-zinc-500">
                加入想去的景點、車站或餐廳，從地圖開始安排。
              </p>
              <Link
                href={`/trips/${trip.id}/activities/new?day=${day}`}
                className="mt-5 inline-block rounded-xl bg-teal-700 px-5 py-3 text-sm text-white"
              >
                安排第一個活動
              </Link>
            </div>
          ) : (
            <ol className="space-y-4">
              {today.map((activity, index) => card(activity, index))}
            </ol>
          )}
          {(legs.length > 0 || stays.length > 0) && (
            <section className="mt-6 rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
              <h3 className="font-semibold">當日交通</h3>
              <p className="mt-2 text-xs leading-6 text-zinc-500">
                依活動順序查詢，出發時間可自行調整。住宿可作為當日的起點與終點。
              </p>
              {stays.length > 0 && (
                <div className="mt-4 space-y-3">
                  <label className="block text-sm">
                    出發住宿
                    <select
                      value={hotelId}
                      onChange={(e) => {
                        setHotelId(e.target.value);
                        setLines({});
                      }}
                      className="mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
                    >
                      <option value="">不使用住宿起點</option>
                      {stays.map((stay) => (
                        <option key={stay.id} value={stay.id}>
                          {stay.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={returnHotel}
                      onChange={(e) => {
                        setReturnHotel(e.target.checked);
                        setLines({});
                      }}
                    />
                    最後前往住宿（退房日可取消）
                  </label>
                  {returnHotel && (
                    <label className="block text-sm">
                      抵達住宿
                      <select
                        value={endHotelId}
                        onChange={(e) => {
                          setEndHotelId(e.target.value);
                          setLines({});
                        }}
                        className="mt-2 w-full rounded-xl border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
                      >
                        {stays.map((stay) => (
                          <option key={stay.id} value={stay.id}>
                            {stay.title}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                </div>
              )}
              <div className="mt-4 space-y-3">
                {legs.map(({ origin, destination }) => (
                  <RouteLeg
                    key={`${origin.id}-${destination.id}`}
                    trip={trip}
                    day={day}
                    origin={origin}
                    destination={destination}
                    onRoute={onRoute}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
        <section
          className={`${view === "map" ? "block" : "hidden"} overflow-hidden rounded-2xl border border-zinc-200 bg-white lg:sticky lg:top-5 lg:block dark:border-zinc-800 dark:bg-zinc-900`}
          aria-label="旅程地圖"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-100 p-4 dark:border-zinc-800">
            <h3 className="font-semibold">看地圖，排得更順</h3>
            <select
              aria-label="地圖日期範圍"
              value={allDays ? "all" : "day"}
              onChange={(e) => {
                setAllDays(e.target.value === "all");
                setSelected(null);
              }}
              className="rounded-lg border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
            >
              <option value="day">當天位置</option>
              <option value="all">整趟旅程</option>
            </select>
          </div>
          <TripMap
            points={mapData.points}
            selectedId={selected}
            onSelect={selectActivity}
            polylines={Object.entries(lines)
              .filter(([id, line]) => line && visibleLegs.has(id))
              .map(([, line]) => line)}
            refreshKey={view}
          />
          <div className="space-y-2 p-4 text-xs text-zinc-500">
            <div className="flex flex-wrap gap-3">
              {Object.values(categories).map((category) => (
                <span key={category.label} className="flex items-center gap-1">
                  <span
                    style={{ backgroundColor: category.color }}
                    className="h-2 w-2 rounded-full"
                  />
                  {category.label}
                </span>
              ))}
            </div>
            {loadingMap && <p role="status">更新地點中…</p>}
            {mapError && (
              <p role="alert" className="text-red-700 dark:text-red-300">
                {mapError}
              </p>
            )}
            {mapData.unavailable_ids.length > 0 && (
              <p>有 {mapData.unavailable_ids.length} 個地點暫時無法定位。</p>
            )}
            <button
              type="button"
              disabled={loadingMap}
              onClick={() => setReload((value) => value + 1)}
              className="py-1 text-teal-700 underline disabled:opacity-50 dark:text-teal-300"
            >
              重新載入地點
            </button>
            {selected &&
              mapData.points.find(
                (point) => point.activity_id === selected,
              ) && (
                <p className="leading-6">
                  {
                    mapData.points.find(
                      (point) => point.activity_id === selected,
                    )?.name
                  }{" "}
                  ·{" "}
                  {
                    mapData.points.find(
                      (point) => point.activity_id === selected,
                    )?.address
                  }
                </p>
              )}
          </div>
        </section>
      </div>
    </>
  );
}
