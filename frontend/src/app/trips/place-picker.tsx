"use client";

import { useState, useTransition } from "react";
import { searchPlaces } from "./planner-actions";
import type { Place } from "@/lib/planner-types";

export default function PlacePicker({
  tripId,
  initialId,
}: {
  tripId: number;
  initialId: string;
}) {
  const [placeId, setPlaceId] = useState(initialId);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Place>();
  const [results, setResults] = useState<Place[]>([]);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const [pending, startTransition] = useTransition();
  return (
    <section className="rounded-2xl border border-teal-200 bg-teal-50/40 p-4 dark:border-teal-900 dark:bg-teal-950/20">
      <h3 className="text-sm font-semibold">連結地圖位置（選填）</h3>
      <p className="mt-1 text-xs leading-6 text-zinc-500">
        選取實際地點後，就能在行程地圖查看位置與交通時間。搜尋時加上城市較容易找到。
      </p>
      <input type="hidden" name="place_id" value={placeId} />
      <div className="mt-3 flex gap-2">
        <input
          aria-label="搜尋地圖地點"
          maxLength={200}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              document.getElementById("place-search-button")?.click();
            }
          }}
          placeholder="例如：東京車站、台北故宮"
          className="min-w-0 flex-1 rounded-xl border border-zinc-300 bg-white px-3 py-2 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          id="place-search-button"
          type="button"
          disabled={pending}
          onClick={() =>
            startTransition(async () => {
              const result = await searchPlaces(tripId, query);
              setResults(result.places ?? []);
              setError(result.error ?? "");
              setSearched(true);
            })
          }
          className="rounded-xl bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {pending ? "搜尋中…" : "搜尋"}
        </button>
      </div>
      <div aria-live="polite">
        {error && (
          <p
            role="alert"
            className="mt-3 text-sm text-red-700 dark:text-red-300"
          >
            {error}
          </p>
        )}
        {!error && searched && !pending && results.length === 0 && (
          <p className="mt-3 text-sm text-zinc-500">
            找不到地點，試著加上城市或地址。
          </p>
        )}
      </div>
      {results.length > 0 && (
        <ul className="mt-3 divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-white dark:divide-zinc-800 dark:border-zinc-800 dark:bg-zinc-900">
          {results.map((place) => (
            <li key={place.place_id}>
              <button
                type="button"
                onClick={() => {
                  setPlaceId(place.place_id);
                  setSelected(place);
                  setResults([]);
                  setSearched(false);
                }}
                className="w-full p-3 text-left hover:bg-teal-50 dark:hover:bg-teal-950"
              >
                <span className="block text-sm font-semibold">
                  {place.name}
                </span>
                <span className="mt-1 block text-xs text-zinc-500">
                  {place.address}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {placeId && (
        <div className="mt-3 flex items-start justify-between gap-3 rounded-xl bg-white p-3 text-sm dark:bg-zinc-900">
          <div>
            <p className="font-medium text-teal-800 dark:text-teal-300">
              ✓ {selected?.name ?? "已連結地圖位置"}
            </p>
            {selected && (
              <p className="mt-1 text-xs text-zinc-500">{selected.address}</p>
            )}
          </div>
          <button
            type="button"
            className="shrink-0 text-xs underline"
            onClick={() => {
              setPlaceId("");
              setSelected(undefined);
            }}
          >
            解除連結
          </button>
        </div>
      )}
      <p className="mt-3 text-right text-xs text-zinc-500" translate="no">
        Google Maps
      </p>
    </section>
  );
}
