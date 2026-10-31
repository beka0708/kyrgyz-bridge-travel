// Loaded on every page: styles, Alpine for small interactions, scroll effects.
import "@/styles/main.css";

import collapse from "@alpinejs/collapse";
import Alpine from "alpinejs";

import { initAnalytics, registerConsent } from "@/lib/analytics";
import { registerHome } from "@/lib/home";
import { registerInquiry } from "@/lib/inquiry";
import { initReveal, initScrollProgress } from "@/lib/scroll";
import { registerTourPage } from "@/lib/tour-page";

/** Alpine's collapse plugin ignores «reduce motion»: make accordions open instantly there. */
function instantCollapseForReducedMotion() {
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  document.querySelectorAll("*").forEach((el) => {
    for (const { name } of Array.from(el.attributes)) {
      if (!name.startsWith("x-collapse")) continue;
      el.removeAttribute(name);
      el.setAttribute("x-collapse.duration.1ms", "");
    }
  });
}

Alpine.plugin(collapse);
instantCollapseForReducedMotion();
registerConsent(Alpine);
registerHome(Alpine);
registerInquiry(Alpine);
registerTourPage(Alpine);
window.Alpine = Alpine;
Alpine.start();

initReveal();
initScrollProgress();
initAnalytics();
