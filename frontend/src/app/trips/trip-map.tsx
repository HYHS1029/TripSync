"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import { categories, type MapPoint } from "@/lib/planner-types";
import { decodePolyline, type GoogleMap } from "@/lib/maps-browser";

export default function TripMap({
  points,
  selectedId,
  onSelect,
  polylines,
  refreshKey,
}: {
  points: MapPoint[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  polylines: string[];
  refreshKey: string;
}) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<GoogleMap | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const sdk = window.google?.maps;
    if (!ready || !sdk || !container.current) return;
    if (!map.current)
      map.current = new sdk.Map(container.current, {
        center: points[0] ?? { lat: 25.033, lng: 121.5654 },
        zoom: 12,
        mapId: process.env.NEXT_PUBLIC_GOOGLE_MAP_ID || "DEMO_MAP_ID",
        mapTypeControl: false,
        streetViewControl: false,
      });
    const bounds = new sdk.LatLngBounds();
    const markers = points.map((point, index) => {
      const category = categories[point.category] ?? categories.other;
      const content = document.createElement("div");
      content.textContent =
        point.category === "lodging" ? "宿" : String(index + 1);
      content.style.cssText = `background:${category.color};color:white;border:3px solid white;border-radius:50%;width:36px;height:36px;display:grid;place-items:center;font-weight:700;box-shadow:0 2px 6px #0005;cursor:pointer`;
      const marker = new sdk.marker.AdvancedMarkerElement({
        map: map.current,
        position: { lat: point.lat, lng: point.lng },
        title: `${point.title} · ${point.name}`,
        content,
      });
      const listener = marker.addListener("click", () =>
        onSelect(point.activity_id),
      );
      bounds.extend(point);
      return { marker, listener };
    });
    if (points.length > 1) map.current.fitBounds(bounds, 48);
    else if (points.length === 1) {
      map.current.panTo(points[0]);
      map.current.setZoom(14);
    }
    return () => {
      for (const { marker, listener } of markers) {
        listener.remove();
        marker.map = null;
      }
    };
  }, [ready, points, onSelect, refreshKey]);
  useEffect(() => {
    const selected = points.find((point) => point.activity_id === selectedId);
    if (selected && map.current) {
      map.current.panTo(selected);
      map.current.setZoom(15);
    }
  }, [selectedId, points, ready]);
  useEffect(() => {
    const sdk = window.google?.maps;
    if (!ready || !sdk || !map.current) return;
    const lines = polylines.flatMap((encoded, index) => {
      try {
        return [
          new sdk.Polyline({
            map: map.current,
            path: decodePolyline(encoded),
            strokeColor: index % 2 ? "#2563eb" : "#0f766e",
            strokeWeight: 5,
            strokeOpacity: 0.8,
          }),
        ];
      } catch {
        return [];
      }
    });
    return () => lines.forEach((line) => line.setMap(null));
  }, [polylines, ready]);
  if (!apiKey)
    return (
      <div className="flex min-h-80 items-center justify-center bg-teal-50/50 p-8 text-center dark:bg-teal-950/20">
        <div>
          <p className="text-3xl" aria-hidden="true">
            ⌖
          </p>
          <h3 className="mt-3 font-semibold">旅程地圖尚未啟用</h3>
          <p className="mt-2 max-w-xs text-sm leading-7 text-zinc-500">
            完成地圖服務設定後，這裡會顯示景點、車站與住宿的位置。你仍可安排活動與記帳。
          </p>
        </div>
      </div>
    );
  return (
    <>
      <Script
        id="tripsync-google-maps"
        src={`https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&v=weekly&libraries=marker&language=zh-TW`}
        strategy="afterInteractive"
        onReady={() => setReady(true)}
        onError={() => setError("地圖暫時無法載入，請確認網路後重新整理。")}
      />
      {error && (
        <p role="alert" className="p-4 text-sm text-red-700">
          {error}
        </p>
      )}
      {!ready && !error && (
        <p role="status" className="p-4 text-sm text-zinc-500">
          載入地圖中…
        </p>
      )}
      <div
        ref={container}
        aria-label="景點、車站與住宿的互動地圖"
        className="h-[440px] w-full sm:h-[560px]"
      />
    </>
  );
}
