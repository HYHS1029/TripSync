export type Coordinate = { lat: number; lng: number };
export type GoogleMap = {
  fitBounds(bounds: unknown, padding?: number): void;
  panTo(point: Coordinate): void;
  setZoom(zoom: number): void;
};
type Marker = {
  map: GoogleMap | null;
  addListener(event: string, callback: () => void): { remove(): void };
};
type Polyline = { setMap(map: GoogleMap | null): void };
export type MapsSDK = {
  Map: new (
    element: HTMLElement,
    options: Record<string, unknown>,
  ) => GoogleMap;
  LatLngBounds: new () => { extend(point: Coordinate): void };
  Polyline: new (options: Record<string, unknown>) => Polyline;
  marker: {
    AdvancedMarkerElement: new (options: Record<string, unknown>) => Marker;
  };
};
declare global {
  interface Window {
    google?: { maps: MapsSDK };
  }
}

export function decodePolyline(encoded: string): Coordinate[] {
  const points: Coordinate[] = [];
  let index = 0,
    lat = 0,
    lng = 0;
  function component() {
    let value = 0,
      shift = 0,
      byte: number;
    do {
      if (index >= encoded.length || shift > 30)
        throw new Error("Invalid route geometry");
      byte = encoded.charCodeAt(index++) - 63;
      if (byte < 0 || byte > 63) throw new Error("Invalid route geometry");
      value |= (byte & 31) << shift;
      shift += 5;
    } while (byte >= 32);
    return value & 1 ? ~(value >> 1) : value >> 1;
  }
  while (index < encoded.length) {
    lat += component();
    lng += component();
    points.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }
  return points;
}
