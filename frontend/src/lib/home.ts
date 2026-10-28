import type { Alpine as AlpineType } from "alpinejs";

/** Home page widgets: «Season hits» carousel and the tour type filter. */
export function registerHome(Alpine: AlpineType) {
  // Three visible slides: previous and next are smaller and dimmed (mockup «HITS»).
  Alpine.data("carousel", (count: number) => ({
    index: 0,
    count,
    role(i: number): "current" | "prev" | "next" | "hidden" {
      if (i === this.index) return "current";
      if (this.count > 1 && i === (this.index + 1) % this.count) return "next";
      if (this.count > 2 && i === (this.index - 1 + this.count) % this.count) return "prev";
      return "hidden";
    },
    go(i: number) {
      this.index = (i + this.count) % this.count;
    },
    prev() {
      this.go(this.index - 1);
    },
    next() {
      this.go(this.index + 1);
    },
  }));

  Alpine.data("tourFilter", () => ({
    type: "all",
    shows(tourType: string) {
      return this.type === "all" || this.type === tourType;
    },
  }));
}
