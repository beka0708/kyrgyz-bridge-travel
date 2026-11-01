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

  /** Photo strip (swipe on phones, arrows on desktop) and a full-screen viewer. */
  Alpine.data("gallery", (count: number) => ({
    count,
    index: 0,
    lightboxIndex: 0,
    open: false,
    opener: null as HTMLElement | null,
    track() {
      return this.$refs.track as HTMLElement;
    },
    onScroll() {
      const el = this.track();
      this.index = Math.round(el.scrollLeft / el.clientWidth);
    },
    step(direction: number) {
      const el = this.track();
      el.scrollBy({ left: direction * el.clientWidth * 0.7, behavior: "smooth" });
    },
    show(i: number) {
      this.opener = document.activeElement as HTMLElement | null;
      this.open = true;
      document.documentElement.style.overflow = "hidden";
      this.$nextTick(() => {
        const box = this.$refs.lightbox as HTMLElement;
        box.scrollTo({ left: i * box.clientWidth, behavior: "instant" });
        this.lightboxIndex = i;
        (this.$refs.close as HTMLElement).focus();
      });
    },
    close() {
      if (!this.open) return;
      this.open = false;
      document.documentElement.style.overflow = "";
      this.opener?.focus();
    },
    onLightboxScroll() {
      const box = this.$refs.lightbox as HTMLElement;
      this.lightboxIndex = Math.round(box.scrollLeft / box.clientWidth);
    },
    lightboxStep(direction: number) {
      const box = this.$refs.lightbox as HTMLElement;
      const next = Math.min(this.count - 1, Math.max(0, this.lightboxIndex + direction));
      box.scrollTo({ left: next * box.clientWidth, behavior: "smooth" });
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
