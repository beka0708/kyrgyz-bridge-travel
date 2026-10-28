// The only module that knows which map library and tile providers we use.
// Switching provider = changing this file and the MAP_* settings on the backend.
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 loads its web worker from a URL; let Vite emit the file and give us its path.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "./map.css";

export type Map3DMode = "off" | "desktop" | "all";
export type BaseLayer = "map" | "topo";

export interface MapConfig {
  style_url: string;
  topo: { tiles: string[]; attribution: string };
  terrain: { tiles: string; encoding: "terrarium" | "mapbox"; attribution: string };
  terrain_3d: Map3DMode;
}

export interface CreateMapOptions {
  center?: [number, number];
  zoom?: number;
  /** 3D tilt + terrain; hillshade is always on. */
  enable3d?: boolean;
  /** Require two fingers / ctrl+scroll so the page scrolls past the map. */
  cooperativeGestures?: boolean;
}

// Kyrgyzstan overview, used when a route has no points yet.
export const KYRGYZSTAN_CENTER: [number, number] = [74.6, 41.4];
export const KYRGYZSTAN_ZOOM = 5.8;

const TOPO_LAYER = "base-topo";
const HILLSHADE_LAYER = "relief-hillshade";
const DESKTOP_QUERY = "(min-width: 1024px) and (pointer: fine)";

maplibregl.setWorkerUrl(workerUrl);

// Resolves when relief/topo layers are added (style loaded), see whenReady().
const ready = new WeakMap<maplibregl.Map, Promise<void>>();

export const prefersReducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function is3dAllowed(mode: Map3DMode): boolean {
  if (mode === "all") return true;
  if (mode === "desktop") return window.matchMedia(DESKTOP_QUERY).matches;
  return false;
}

export function createMap(
  container: HTMLElement,
  config: MapConfig,
  options: CreateMapOptions = {},
): maplibregl.Map {
  const enable3d = options.enable3d ?? false;
  const map = new maplibregl.Map({
    container,
    style: config.style_url,
    center: options.center ?? KYRGYZSTAN_CENTER,
    zoom: options.zoom ?? KYRGYZSTAN_ZOOM,
    pitch: enable3d ? 50 : 0,
    maxPitch: enable3d ? 70 : 0,
    attributionControl: { compact: true },
    cooperativeGestures: options.cooperativeGestures ?? false,
  });
  map.addControl(
    new maplibregl.NavigationControl({ showCompass: enable3d, visualizePitch: enable3d }),
  );
  map.addControl(new BaseLayerControl(map), "top-left");
  ready.set(
    map,
    new Promise((resolve) =>
      map.once("load", () => {
        addRelief(map, config, enable3d);
        // Compact attribution starts expanded and covers a phone-sized map; keep it behind ⓘ.
        container.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show");
        resolve();
      }),
    ),
  );
  return map;
}

function addRelief(map: maplibregl.Map, config: MapConfig, enable3d: boolean) {
  const dem = {
    type: "raster-dem" as const,
    tiles: [config.terrain.tiles],
    encoding: config.terrain.encoding,
    tileSize: 256,
    maxzoom: 14,
    attribution: config.terrain.attribution,
  };
  // Hillshade under labels so place names stay readable.
  const firstSymbol = map.getStyle().layers.find((l) => l.type === "symbol")?.id;
  map.addSource("relief-dem", dem);
  map.addLayer(
    {
      id: HILLSHADE_LAYER,
      type: "hillshade",
      source: "relief-dem",
      paint: { "hillshade-exaggeration": 0.55, "hillshade-shadow-color": "#3d3a33" },
    },
    firstSymbol,
  );
  if (enable3d) {
    // A separate source for terrain avoids hillshade artifacts (MapLibre recommendation).
    map.addSource("terrain-dem", dem);
    map.setTerrain({ source: "terrain-dem", exaggeration: 1.3 });
  }

  map.addSource("topo", {
    type: "raster",
    tiles: config.topo.tiles,
    tileSize: 256,
    maxzoom: 17,
    attribution: config.topo.attribution,
  });
  map.addLayer({
    id: TOPO_LAYER,
    type: "raster",
    source: "topo",
    layout: { visibility: "none" },
  });
}

export function setBaseLayer(map: maplibregl.Map, layer: BaseLayer) {
  if (!map.getLayer(TOPO_LAYER)) return;
  const topo = layer === "topo";
  map.setLayoutProperty(TOPO_LAYER, "visibility", topo ? "visible" : "none");
  // OpenTopoMap has its own relief shading.
  map.setLayoutProperty(HILLSHADE_LAYER, "visibility", topo ? "none" : "visible");
}

/** «Map / Topo» switch; topo shows trails, passes and contour lines. */
class BaseLayerControl implements maplibregl.IControl {
  private container?: HTMLDivElement;

  constructor(private readonly map: maplibregl.Map) {}

  onAdd() {
    const box = document.createElement("div");
    box.className = "maplibregl-ctrl maplibregl-ctrl-group kt-baselayer";
    const buttons = (["map", "topo"] as const).map((layer) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = layer === "map" ? "Map" : "Topo";
      button.setAttribute("aria-pressed", String(layer === "map"));
      button.onclick = () => {
        setBaseLayer(this.map, layer);
        buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
      };
      box.append(button);
      return button;
    });
    this.container = box;
    return box;
  }

  onRemove() {
    this.container?.remove();
  }
}

/** Resolves once the style and the relief/topo layers are in place. */
export function whenReady(map: maplibregl.Map): Promise<void> {
  return ready.get(map) ?? Promise.resolve();
}

export { maplibregl };
