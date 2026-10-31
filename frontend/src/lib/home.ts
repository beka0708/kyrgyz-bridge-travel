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
    /** Position of slide i: current in the middle, neighbours smaller and dimmed at the sides. */
    slideStyle(i: number) {
      const role = this.role(i);
      if (role === "current") return "transform: translate(-50%, -50%) scale(1); opacity: 1";
      if (role === "prev" || role === "next") {
        const x = role === "prev" ? "-142%" : "42%";
        return `transform: translate(${x}, -50%) scale(.78); opacity: .55`;
      }
      // off-stage slides wait behind the side ones, ready to slide in
      const ahead = (i - this.index + this.count) % this.count <= this.count / 2;
      return `transform: translate(${ahead ? "90%" : "-190%"}, -50%) scale(.6); opacity: 0; pointer-events: none`;
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
