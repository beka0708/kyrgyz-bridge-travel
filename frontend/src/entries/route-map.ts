// Tiny entry: the map library (~1 MB) is fetched only when the map is about to be seen,
// so the first screen on a phone does not pay for it.
import { createApp } from "vue";

function mount(el: HTMLElement) {
  if (el.dataset.mounted) return;
  el.dataset.mounted = "true";
  const source = el.dataset.propsId ? document.getElementById(el.dataset.propsId) : null;
  const props = source?.textContent ? JSON.parse(source.textContent) : {};
  import("@/components/RouteMap.vue").then(({ default: RouteMap }) => {
    createApp(RouteMap, props).mount(el);
  });
}

const islands = document.querySelectorAll<HTMLElement>('[data-island="route-map"]');
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        mount(entry.target as HTMLElement);
      }
    },
    { rootMargin: "400px 0px" },
  );
  islands.forEach((el) => observer.observe(el));
} else {
  islands.forEach(mount);
}
