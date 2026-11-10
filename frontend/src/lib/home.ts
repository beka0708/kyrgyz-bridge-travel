import type { Alpine as AlpineType } from "alpinejs";

export function registerHome(Alpine: AlpineType) {
  /** Tour filter chips: a tour shows when its tags («solo short») include the chosen one. */
  Alpine.data("tourFilter", () => ({
    filter: "all",
    init() {
      this.$watch("filter", (value: string) => window.dispatchEvent(new CustomEvent("tours:filter", { detail: value })));
    },
    shows(tags: string) {
      return this.filter === "all" || tags.split(" ").includes(this.filter);
    },
  }));

  /**
   * Tour card photos, switched only by the visitor: arrows (mouse) or a swipe (touch).
   * Extra photos are added to the page (and downloaded) once the card is on screen.
   */
  Alpine.data("cardSlides", (count: number) => ({
    count,
    index: 0,
    loaded: false,
    touchX: 0,
    init() {
      if (this.count < 2) return;
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (!entry.isIntersecting) return;
          this.loaded = true;
          observer.disconnect();
        },
        { rootMargin: "200px 0px" },
      );
      observer.observe(this.$el);
    },
    step(direction: number) {
      this.loaded = true;
      this.index = (this.index + direction + this.count) % this.count;
    },
    swipeStart(event: TouchEvent) {
      this.touchX = event.touches[0].clientX;
    },
    swipeEnd(event: TouchEvent) {
      const dx = event.changedTouches[0].clientX - this.touchX;
      if (Math.abs(dx) > 40) this.step(dx < 0 ? 1 : -1);
    },
  }));
}
