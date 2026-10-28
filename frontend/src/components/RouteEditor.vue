<script setup lang="ts">
// Admin: place a day's points on the map and preview the route line before saving.
// The points are written to the form's hidden `waypoints` field; the server builds and
// stores the final line on save, so this preview never has to be "applied".
import type { LineString } from "geojson";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { createMap, maplibregl, whenReady, type MapConfig } from "@/map/provider";
import {
  addRouteLayers,
  boundsOf,
  fitTo,
  setRouteData,
  type RouteDay,
  type Waypoint,
} from "@/map/route";

interface RouteResult {
  track: LineString | null;
  distance_km: string | null;
  ascent_m: number | null;
  waypoints?: Waypoint[] | null;
}

const props = defineProps<{
  map: MapConfig;
  track: LineString | null;
  api: { build: string; gpx: string };
  input: HTMLTextAreaElement;
  sourceField: string;
  gpxField: string;
}>();

const points = ref<Waypoint[]>(parseInitial(props.input.value));
const track = ref<LineString | null>(props.track);
// What the shown line was built from; when points change the line is marked stale.
const builtFrom = ref(props.track ? fingerprint() : "");
const status = ref<{ kind: "info" | "ok" | "error"; text: string } | null>(null);
const busy = ref(false);
const container = ref<HTMLDivElement>();

let map: maplibregl.Map | undefined;
let markers: maplibregl.Marker[] = [];

const stale = computed(() => track.value !== null && builtFrom.value !== fingerprint());

function parseInitial(raw: string): Waypoint[] {
  try {
    const value = JSON.parse(raw || "[]");
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

function fingerprint() {
  return JSON.stringify([sourceValue(), points.value.map((p) => [p.lat, p.lng])]);
}

function sourceValue(): string {
  return (document.getElementById(props.sourceField) as HTMLSelectElement | null)?.value ?? "manual";
}

function round(value: number) {
  return Math.round(value * 1e6) / 1e6;
}

const day = computed<RouteDay>(() => ({
  day_number: 1,
  title: "",
  waypoints: points.value,
  // A stale line would mislead, so fall back to the dashed preview through the points.
  track: stale.value ? null : track.value,
}));

function render() {
  if (!map?.getSource("edit-lines")) return;
  setRouteData(map, [day.value], null, "edit");
  renderMarkers();
}

function renderMarkers() {
  markers.forEach((m) => m.remove());
  markers = points.value.map((point, index) => {
    const el = document.createElement("div");
    el.className = "kt-editor-marker";
    el.textContent = String(index + 1);
    el.title = point.name || `Точка ${index + 1}`;
    const marker = new maplibregl.Marker({ element: el, draggable: true })
      .setLngLat([point.lng, point.lat])
      .addTo(map!);
    marker.on("dragend", () => {
      const { lng, lat } = marker.getLngLat();
      points.value[index] = { ...points.value[index], lat: round(lat), lng: round(lng) };
    });
    return marker;
  });
}

function addPoint(e: maplibregl.MapMouseEvent) {
  points.value.push({ lat: round(e.lngLat.lat), lng: round(e.lngLat.lng), name: "" });
}

function move(index: number, delta: number) {
  const target = index + delta;
  if (target < 0 || target >= points.value.length) return;
  const list = [...points.value];
  [list[index], list[target]] = [list[target], list[index]];
  points.value = list;
}

function remove(index: number) {
  points.value.splice(index, 1);
}

function clearAll() {
  if (points.value.length && !confirm("Удалить все точки этого дня?")) return;
  points.value = [];
  track.value = null;
  status.value = null;
}

function fit() {
  if (map) fitTo(map, boundsOf([{ waypoints: points.value, track: track.value }]));
}

function csrfToken() {
  return (document.querySelector("[name=csrfmiddlewaretoken]") as HTMLInputElement | null)?.value ?? "";
}

async function call(url: string, body: BodyInit, json: boolean): Promise<RouteResult> {
  const response = await fetch(url, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": csrfToken(),
      ...(json ? { "Content-Type": "application/json" } : {}),
    },
    body,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      data.detail ?? Object.values(data).flat().join(" ") ?? `Ошибка ${response.status}`;
    throw new Error(String(detail || `Ошибка ${response.status}`));
  }
  return data as RouteResult;
}

async function build() {
  const source = sourceValue();
  busy.value = true;
  status.value = { kind: "info", text: "Строим линию…" };
  try {
    let result: RouteResult;
    if (source === "gpx") {
      const file = (document.getElementById(props.gpxField) as HTMLInputElement | null)?.files?.[0];
      if (!file) {
        status.value = {
          kind: "info",
          text: "Выберите GPX-файл в поле ниже. Если файл уже загружен — просто сохраните день.",
        };
        return;
      }
      const form = new FormData();
      form.append("file", file);
      result = await call(props.api.gpx, form, false);
      if (result.waypoints?.length && !points.value.length) points.value = result.waypoints;
    } else {
      result = await call(
        props.api.build,
        JSON.stringify({ source, waypoints: points.value }),
        true,
      );
    }
    track.value = result.track;
    builtFrom.value = fingerprint();
    const parts = [
      result.distance_km && `≈ ${result.distance_km} км`,
      result.ascent_m != null && `набор ${result.ascent_m} м`,
    ].filter(Boolean);
    status.value = {
      kind: "ok",
      text: `Линия построена${parts.length ? ": " + parts.join(", ") : ""}. Нажмите «Сохранить», чтобы она попала на сайт.`,
    };
    fit();
  } catch (error) {
    status.value = { kind: "error", text: (error as Error).message };
  } finally {
    busy.value = false;
  }
}

watch(
  points,
  (value) => {
    props.input.value = JSON.stringify(
      value.map((p) => ({ lat: round(p.lat), lng: round(p.lng), name: (p.name ?? "").trim() })),
    );
    render();
  },
  { deep: true },
);

onMounted(async () => {
  map = createMap(container.value!, props.map, { enable3d: false });
  map.on("click", addPoint);
  map.getCanvas().style.cursor = "crosshair";
  document.getElementById(props.sourceField)?.addEventListener("change", render);
  await whenReady(map);
  addRouteLayers(map, "edit");
  render();
  fitTo(map, boundsOf([{ waypoints: points.value, track: track.value }]), { animate: false });
});

onBeforeUnmount(() => map?.remove());
</script>

<template>
  <div class="kt-editor">
    <p class="kt-editor__hint">
      Кликните по карте, чтобы добавить точку. Точки можно перетаскивать. Порядок точек — порядок
      маршрута. «Topo» показывает тропы и перевалы.
    </p>
    <div ref="container" class="kt-editor__map" />

    <div class="kt-editor__toolbar">
      <button type="button" class="kt-btn kt-btn--primary" :disabled="busy" @click="build">
        {{ busy ? "Строим…" : "Построить линию" }}
      </button>
      <button type="button" class="kt-btn" :disabled="!points.length" @click="fit">
        Показать маршрут
      </button>
      <button type="button" class="kt-btn kt-btn--danger" :disabled="!points.length" @click="clearAll">
        Очистить
      </button>
      <span class="kt-editor__count">Точек: {{ points.length }}</span>
    </div>

    <p v-if="stale" class="kt-editor__status kt-editor__status--info">
      Точки изменились — пунктир показывает порядок. Постройте линию заново или сохраните день.
    </p>
    <p v-if="status" :class="['kt-editor__status', `kt-editor__status--${status.kind}`]">
      {{ status.text }}
    </p>

    <ol v-if="points.length" class="kt-editor__list">
      <li v-for="(point, index) in points" :key="index">
        <span class="kt-editor__num">{{ index + 1 }}</span>
        <input
          v-model="point.name"
          type="text"
          maxlength="80"
          placeholder="Название (необязательно), напр. Karakol"
        />
        <span class="kt-editor__coords">{{ point.lat.toFixed(4) }}, {{ point.lng.toFixed(4) }}</span>
        <button type="button" title="Выше" :disabled="index === 0" @click="move(index, -1)">↑</button>
        <button
          type="button"
          title="Ниже"
          :disabled="index === points.length - 1"
          @click="move(index, 1)"
        >
          ↓
        </button>
        <button type="button" title="Удалить" @click="remove(index)">✕</button>
      </li>
    </ol>
  </div>
</template>

<style>
/* Plain CSS: it must look right inside unfold's admin in light and dark themes. */
.kt-editor {
  width: 100%;
}
.kt-editor__hint {
  margin: 0 0 8px;
  font-size: 13px;
  opacity: 0.75;
}
.kt-editor__map {
  height: 460px;
  border-radius: 8px;
  overflow: hidden;
}
.kt-editor__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}
.kt-btn {
  border: 1px solid rgb(128 128 128 / 0.35);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: inherit;
}
.kt-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.kt-btn--primary {
  background: #e8964a;
  border-color: #e8964a;
  color: #fff;
}
.kt-btn--danger {
  color: #dc2626;
}
.kt-editor__count {
  margin-left: auto;
  font-size: 13px;
  opacity: 0.7;
}
.kt-editor__status {
  margin: 8px 0 0;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
}
.kt-editor__status--info {
  background: rgb(59 130 246 / 0.12);
}
.kt-editor__status--ok {
  background: rgb(34 197 94 / 0.15);
}
.kt-editor__status--error {
  background: rgb(239 68 68 / 0.15);
  color: #dc2626;
}
.kt-editor__list {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
}
.kt-editor__list li {
  display: flex;
  align-items: center;
  gap: 8px;
}
.kt-editor__list input {
  flex: 1;
  min-width: 0;
  padding: 5px 8px;
  border: 1px solid rgb(128 128 128 / 0.35);
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font-size: 13px;
}
.kt-editor__list button {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 4px 6px;
  opacity: 0.7;
}
.kt-editor__list button:disabled {
  opacity: 0.2;
}
.kt-editor__num,
.kt-editor-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e8964a;
  color: #fff;
  font: 700 12px/1 system-ui, sans-serif;
  flex: none;
}
.kt-editor-marker {
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgb(0 0 0 / 0.4);
  cursor: grab;
}
.kt-editor__coords {
  font-size: 12px;
  opacity: 0.6;
  font-variant-numeric: tabular-nums;
}
</style>
