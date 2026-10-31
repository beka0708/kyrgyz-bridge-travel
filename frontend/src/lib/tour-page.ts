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

  // WAI-ARIA tabs: arrows move between tabs (and select them), Home/End jump to the ends.
  Alpine.data("tabs", (first: string) => ({
    tab: first,
    onKey(event: KeyboardEvent) {
      const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];
      if (!keys.includes(event.key)) return;
      const list = event.currentTarget as HTMLElement;
      const tabs = Array.from(list.querySelectorAll<HTMLButtonElement>("[role=tab]"));
      const current = tabs.findIndex((el) => el.dataset.tab === this.tab);
      let next = current;
      if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (current + 1) % tabs.length;
      else next = (current - 1 + tabs.length) % tabs.length;
      event.preventDefault();
      this.tab = tabs[next].dataset.tab!;
      tabs[next].focus();
    },
  }));
}
