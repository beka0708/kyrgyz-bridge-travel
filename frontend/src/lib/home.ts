import type { Alpine as AlpineType } from "alpinejs";

/** Tour filter chips: a tour shows when its tags («solo short») include the chosen one. */
export function registerHome(Alpine: AlpineType) {
  Alpine.data("tourFilter", () => ({
    filter: "all",
    shows(tags: string) {
      return this.filter === "all" || tags.split(" ").includes(this.filter);
    },
  }));
}
