export const categories: Record<
  string,
  { label: string; icon: string; color: string }
> = {
  sight: { label: "景點", icon: "景", color: "#0f766e" },
  station: { label: "車站", icon: "站", color: "#2563eb" },
  lodging: { label: "住宿", icon: "宿", color: "#9333ea" },
  food: { label: "餐飲", icon: "食", color: "#ea580c" },
  other: { label: "其他", icon: "點", color: "#64748b" },
};
export type Place = {
  place_id: string;
  name: string;
  address: string;
  lat: number;
  lng: number;
};
export type MapPoint = Place & {
  activity_id: number;
  category: string;
  title: string;
  day: string;
};
export type MapData = {
  points: MapPoint[];
  unavailable_ids: number[];
  queried_at: string;
};
export type RouteResult = {
  status: "ok" | "no_route" | "date_unavailable";
  message?: string;
  minutes?: number;
  distance_meters?: number;
  polyline?: string;
  steps?: { line: string; from: string; to: string }[];
  time_conflict?: boolean;
  departure_at?: string;
  arrival_at?: string;
  queried_at?: string;
};
