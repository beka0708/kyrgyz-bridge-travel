// Route drawing shared by the public map and the admin editor.
import type { Feature, FeatureCollection, LineString, Point } from "geojson";

import type { ExpressionSpecification } from "maplibre-gl";

import { maplibregl, prefersReducedMotion } from "./provider";

export interface Waypoint {
  lat: number;
  lng: number;
  name?: string;
}

export interface RouteDay {
  day_number: number;
  title: string;
  waypoints: Waypoint[];
  track: LineString | null;
  track_source?: "manual" | "road" | "hiking" | "gpx";
}

export const COLORS = {
  active: "#e8964a",
  inactive: "#7c7a73",
  casing: "#ffffff",
};

const toLngLat = (p: Waypoint): [number, number] => [p.lng, p.lat];

/** Saved line, or a straight dashed line through the points while there is none. */
export function dayLine(day: Pick<RouteDay, "waypoints" | "track">): {
  coordinates: number[][];
  approximate: boolean;
} | null {
  if (day.track?.coordinates?.length) return { coordinates: day.track.coordinates, approximate: false };
  if (day.waypoints.length >= 2) return { coordinates: day.waypoints.map(toLngLat), approximate: true };
  return null;
}

export function routeFeatures(days: RouteDay[], activeDay: number | null) {
  const lines: Feature<LineString>[] = [];
  const points: Feature<Point>[] = [];
  for (const day of days) {
    const active = activeDay === null || day.day_number === activeDay;
    const line = dayLine(day);
    if (line) {
      lines.push({
        type: "Feature",
        properties: { day: day.day_number, active, approximate: line.approximate },
        geometry: { type: "LineString", coordinates: line.coordinates },
      });
    }
    day.waypoints.forEach((p, i) =>
      points.push({
        type: "Feature",
        properties: { day: day.day_number, active, name: p.name ?? "", index: i },
        geometry: { type: "Point", coordinates: toLngLat(p) },
      }),
    );
  }
  const collection = <T extends LineString | Point>(features: Feature<T>[]): FeatureCollection<T> => ({
    type: "FeatureCollection",
    features,
  });
  return { lines: collection(lines), points: collection(points) };
}

export function addRouteLayers(map: maplibregl.Map, prefix = "route") {
  const empty: FeatureCollection = { type: "FeatureCollection", features: [] };
  map.addSource(`${prefix}-lines`, { type: "geojson", data: empty });
  map.addSource(`${prefix}-points`, { type: "geojson", data: empty });
  const active: ExpressionSpecification = ["get", "active"];
  map.addLayer({
    id: `${prefix}-casing`,
    type: "line",
    source: `${prefix}-lines`,
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": COLORS.casing,
      "line-width": ["case", active, 9, 5],
      "line-opacity": 0.85,
    },
  });
  map.addLayer({
    id: `${prefix}-line`,
    type: "line",
    source: `${prefix}-lines`,
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": ["case", active, COLORS.active, COLORS.inactive],
      "line-width": ["case", active, 5, 3],
    },
  });
  // Straight placeholder lines (no saved track yet) are drawn dashed on top.
  map.setFilter(`${prefix}-line`, ["!", ["get", "approximate"]]);
  map.addLayer({
    id: `${prefix}-line-approx`,
    type: "line",
    source: `${prefix}-lines`,
    filter: ["get", "approximate"],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: {
      "line-color": ["case", active, COLORS.active, COLORS.inactive],
      "line-width": ["case", active, 4, 2.5],
      "line-dasharray": [2, 1.5],
    },
  });
  map.addLayer({
    id: `${prefix}-points`,
    type: "circle",
    source: `${prefix}-points`,
    paint: {
      "circle-radius": ["case", active, 6, 4],
      "circle-color": ["case", active, COLORS.active, COLORS.inactive],
      "circle-stroke-color": "#fff",
      "circle-stroke-width": 2,
    },
  });
}

export function setRouteData(
  map: maplibregl.Map,
  days: RouteDay[],
  activeDay: number | null,
  prefix = "route",
) {
  const { lines, points } = routeFeatures(days, activeDay);
  (map.getSource(`${prefix}-lines`) as maplibregl.GeoJSONSource | undefined)?.setData(lines);
  (map.getSource(`${prefix}-points`) as maplibregl.GeoJSONSource | undefined)?.setData(points);
}

export function boundsOf(days: Pick<RouteDay, "waypoints" | "track">[]): maplibregl.LngLatBounds | null {
  const bounds = new maplibregl.LngLatBounds();
  let any = false;
  for (const day of days) {
    for (const p of day.waypoints) {
      bounds.extend(toLngLat(p));
      any = true;
    }
    for (const [lng, lat] of day.track?.coordinates ?? []) {
      bounds.extend([lng, lat]);
      any = true;
    }
  }
  return any ? bounds : null;
}

export function fitTo(
  map: maplibregl.Map,
  bounds: maplibregl.LngLatBounds | null,
  { animate = true, padding = 60, maxZoom = 12 } = {},
) {
  if (!bounds) return;
  map.fitBounds(bounds, {
    padding,
    maxZoom,
    pitch: map.getPitch(),
    duration: animate && !prefersReducedMotion() ? 900 : 0,
  });
}
