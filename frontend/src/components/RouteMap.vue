<script setup lang="ts">
// Public tour page: the whole route, with the selected day highlighted.
// Day selection comes from the built-in chips or from a `route:day` window event,
// so the server-rendered day list (variant A) can drive the same map.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { createMap, is3dAllowed, whenReady, type MapConfig, maplibregl } from "@/map/provider";
import { addRouteLayers, boundsOf, fitTo, setRouteData, type RouteDay } from "@/map/route";

const props = withDefaults(
  defineProps<{
    map: MapConfig;
    days: RouteDay[];
    initialDay?: number | null;
    showDayChips?: boolean;
  }>(),
  { initialDay: null, showDayChips: true },
);

const activeDay = ref<number | null>(props.initialDay);
const container = ref<HTMLDivElement>();
let map: maplibregl.Map | undefined;

const routedDays = computed(() => props.days.filter((d) => d.waypoints.length || d.track));

const activeTitle = computed(
  () => props.days.find((d) => d.day_number === activeDay.value)?.title ?? "Whole route",
);

/** Google Maps directions for the selected day (or the whole route), up to 10 stops. */
const googleMapsUrl = computed(() => {
  const days = activeDay.value === null ? props.days : props.days.filter((d) => d.day_number === activeDay.value);
  const stops = days.flatMap((d) => d.waypoints).map((p) => `${p.lat},${p.lng}`);
  const unique = stops.filter((s, i) => s !== stops[i - 1]);
  if (unique.length < 2) return unique.length ? `https://www.google.com/maps/search/?api=1&query=${unique[0]}` : "";
  const trimmed = unique.length > 10 ? [unique[0], ...unique.slice(1, -1).slice(0, 8), unique.at(-1)!] : unique;
  const params = new URLSearchParams({
    api: "1",
    origin: trimmed[0],
    destination: trimmed.at(-1)!,
    // Driving only when every shown day follows roads; straight lines and GPX are treks.
    travelmode: days.every((d) => d.track_source === "road") ? "driving" : "walking",
  });
  if (trimmed.length > 2) params.set("waypoints", trimmed.slice(1, -1).join("|"));
  return `https://www.google.com/maps/dir/?${params}`;
});

function select(day: number | null) {
  activeDay.value = day;
}

function onExternalSelect(event: Event) {
  const day = (event as CustomEvent<number | null>).detail;
  select(typeof day === "number" ? day : null);
}

function focusActive(animate = true) {
  if (!map) return;
  const days =
    activeDay.value === null ? routedDays.value : routedDays.value.filter((d) => d.day_number === activeDay.value);
  fitTo(map, boundsOf(days.length ? days : routedDays.value), { animate, padding: 50 });
}

watch(activeDay, () => {
  if (!map) return;
  setRouteData(map, props.days, activeDay.value);
  focusActive();
});

onMounted(async () => {
  window.addEventListener("route:day", onExternalSelect);
  map = createMap(container.value!, props.map, {
    enable3d: is3dAllowed(props.map.terrain_3d),
    cooperativeGestures: true,
  });
  await whenReady(map);
  addRouteLayers(map);
  setRouteData(map, props.days, activeDay.value);
  focusActive(false);
});

onBeforeUnmount(() => {
  window.removeEventListener("route:day", onExternalSelect);
  map?.remove();
});
</script>

<template>
  <div class="kt-route">
    <div v-if="showDayChips" class="kt-route__chips" role="tablist" aria-label="Route days">
      <button
        type="button"
        role="tab"
        :aria-selected="activeDay === null"
        @click="select(null)"
      >
        All days
      </button>
      <button
        v-for="day in days"
        :key="day.day_number"
        type="button"
        role="tab"
        :aria-selected="activeDay === day.day_number"
        @click="select(day.day_number)"
      >
        Day {{ day.day_number }}
      </button>
    </div>
    <div ref="container" class="kt-route__map" :aria-label="`Route map: ${activeTitle}`" role="region" />
    <a v-if="googleMapsUrl" class="kt-route__gmaps" :href="googleMapsUrl" target="_blank" rel="noopener">
      Open in Google Maps ↗
    </a>
  </div>
</template>

<style>
/* Temporary look; the real styles come with the tour page design (Tailwind). */
.kt-route__chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
  scrollbar-width: none;
}
.kt-route__chips button {
  flex: none;
  border: 1px solid #c9c6bb;
  background: #fff;
  border-radius: 999px;
  padding: 7px 14px;
  font: inherit;
  cursor: pointer;
}
.kt-route__chips button[aria-selected="true"] {
  background: #e8964a;
  border-color: #e8964a;
  color: #fff;
}
.kt-route__map {
  height: min(70vh, 520px);
  border-radius: 16px;
  overflow: hidden;
}
@media (max-width: 1023px) {
  .kt-route__map {
    height: 45vh;
  }
}
.kt-route__gmaps {
  display: inline-block;
  margin-top: 8px;
  font-size: 14px;
  color: #b4642a;
}
</style>
