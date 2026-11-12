import type { Alpine as AlpineType } from "alpinejs";

export function registerHome(Alpine: AlpineType) {
  /** Tour filter chips: a tour shows when its tags («solo short») include the chosen one. */
  Alpine.data("tourFilter", (initial: string = "all") => ({
    filter: initial,
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

  /**
   * Reviews «spotlight»: one review at a time. The active face's ring (CSS) fills up and its
   * animationend calls next(), so the pace, the pause on hover and reduced motion live in CSS.
   */
  Alpine.data("reviewSpotlight", (count: number) => ({
    active: 0,
    hover: false,
    visible: false,
    startX: 0,
    init() {
      new IntersectionObserver(([entry]) => (this.visible = entry.isIntersecting), { threshold: 0.3 }).observe(
        this.$el,
      );
    },
    go(index: number) {
      this.active = (index + count) % count;
    },
    next() {
      this.go(this.active + 1);
    },
    swipeStart(e: TouchEvent) {
      this.startX = e.touches[0].clientX;
    },
    swipeEnd(e: TouchEvent) {
      const dx = e.changedTouches[0].clientX - this.startX;
      if (Math.abs(dx) > 50) this.go(this.active + (dx < 0 ? 1 : -1));
    },
  }));

  /**
   * Reviews «deck»: a stack of cards. Drag the top one past ~90px (or press ← →) and it flies off,
   * then settles at the back. cardStyle() gives each card its place (--pos), a slight tilt and,
   * for the top card, the live drag offset.
   */
  Alpine.data("reviewDeck", (count: number) => ({
    top: 0,
    dx: 0,
    dragging: false,
    leaving: -1,
    fly: 1,
    isTop(i: number) {
      return i === this.top;
    },
    cardStyle(i: number) {
      const pos = (i - this.top + count) % count;
      const tilt = pos === 0 ? this.dx * 0.05 : ((i % 3) - 1) * 3;
      const dx = this.isTop(i) ? this.dx : 0;
      return `--pos: ${pos}; --tilt: ${tilt.toFixed(2)}deg; --dx: ${dx}px; --fly: ${this.fly}`;
    },
    throwTop(direction: number) {
      if (this.leaving !== -1 || count < 2) return;
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (direction < 0) {
        // previous: the card at the back comes to the top
        this.dx = 0;
        this.top = (this.top - 1 + count) % count;
        return;
      }
      this.fly = this.dx < 0 ? -1 : 1;
      this.leaving = this.top;
      window.setTimeout(
        () => {
          this.top = (this.top + 1) % count;
          this.leaving = -1;
          this.dx = 0;
        },
        reduce ? 0 : 380,
      );
    },
    dragStart(e: PointerEvent) {
      if (e.button !== 0 || this.leaving !== -1) return;
      const startX = e.clientX;
      this.dragging = true;
      const move = (ev: PointerEvent) => (this.dx = ev.clientX - startX);
      const up = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", up);
        window.removeEventListener("pointercancel", up);
        this.dragging = false;
        if (Math.abs(this.dx) > 90) this.throwTop(1);
        else this.dx = 0;
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", up);
      window.addEventListener("pointercancel", up);
    },
  }));
}
