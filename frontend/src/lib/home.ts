import type { Alpine as AlpineType } from "alpinejs";

/** Home page widgets: the tour type filter. */
export function registerHome(Alpine: AlpineType) {
  Alpine.data("tourFilter", () => ({
    type: "all",
    shows(tourType: string) {
      return this.type === "all" || this.type === tourType;
    },
  }));
}
