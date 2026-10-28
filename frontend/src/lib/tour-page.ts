import type { Alpine as AlpineType } from "alpinejs";

/** Day selection on the tour page; the map island listens to `route:day`. */
export function registerTourPage(Alpine: AlpineType) {
  Alpine.data("tourRoute", (firstDay: number) => ({
    day: firstDay,
    select(day: number) {
      this.day = day;
      window.dispatchEvent(new CustomEvent("route:day", { detail: day }));
    },
  }));

  Alpine.data("tabs", (first: string) => ({
    tab: first,
  }));
}
