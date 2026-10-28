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
const active = computed(() => props.days.find((d) => d.day_number === activeDay.value) ?? null);

/** Google Maps directions for the selected day (or the whole route), up to 10 stops. */
const googleMapsUrl = computed(() => {
  const days = active.value ? [active.value] : props.days;
  const stops = days.flatMap((d) => d.waypoints).map((p) => `${p.lat},${p.lng}`);
  const unique = stops.filter((s, i) => s !== stops[i - 1]);
  if (unique.length < 2) {
    return unique.length ? `https://www.google.com/maps/search/?api=1&query=${unique[0]}` : "";
  }
  const trimmed =
    unique.length > 10 ? [unique[0], ...unique.slice(1, -1).slice(0, 8), unique.at(-1)!] : unique;
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
  const days = active.value && routedDays.value.includes(active.value) ? [active.value] : routedDays.value;
  fitTo(map, boundsOf(days), { animate, padding: 60 });
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
    controls: "bottom",
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
  <div class="flex h-full flex-col">
    <div v-if="showDayChips" class="snap-row pb-2.5" role="tablist" aria-label="Route days">
      <button
        v-for="item in [null, ...days.map((d) => d.day_number)]"
        :key="item ?? 'all'"
        type="button"
        role="tab"
        :aria-selected="activeDay === item"
        class="min-h-11 rounded-full border-[1.5px] px-5 text-sm font-bold"
        :class="activeDay === item ? 'border-accent bg-accent text-ink' : 'border-line-strong text-snow'"
        @click="select(item)"
      >
        {{ item === null ? "All days" : `Day ${item}` }}
      </button>
    </div>
    <div class="relative min-h-0 flex-1">
      <!-- maplibre-gl.css sets the map element to position:relative, so size it via a wrapper -->
      <div class="absolute inset-0">
        <div
          ref="container"
          class="h-full w-full"
          role="region"
          :aria-label="active ? `Route map, day ${active.day_number}: ${active.title}` : 'Route map'"
        />
      </div>
      <!-- Overlays from the mockup: current day on the left, Google Maps on the right -->
      <div class="pointer-events-none absolute inset-x-3 top-3 flex items-start justify-between gap-2 md:inset-x-4 md:top-4">
        <span
          v-if="active"
          class="max-w-[60%] truncate rounded-full bg-night px-3 py-1.5 text-[13px] font-bold text-snow md:px-4 md:py-2 md:text-sm"
        >
          Day {{ active.day_number }}<span class="hidden md:inline">: {{ active.title }}</span>
        </span>
        <span v-else />
        <a
          v-if="googleMapsUrl"
          :href="googleMapsUrl"
          target="_blank"
          rel="noopener"
          class="pointer-events-auto inline-flex min-h-10 items-center rounded-full bg-accent px-3.5 text-[13px] font-bold whitespace-nowrap text-ink md:px-4 md:text-sm"
        >
          <span class="md:hidden">Google Maps</span><span class="hidden md:inline">Open in Google Maps</span>
        </a>
      </div>
    </div>
  </div>
</template>
