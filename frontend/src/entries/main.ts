// Loaded on every page: styles, Alpine for small interactions, scroll effects.
import "@/styles/main.css";

import collapse from "@alpinejs/collapse";
import Alpine from "alpinejs";

import { registerHome } from "@/lib/home";
import { registerInquiry } from "@/lib/inquiry";
import { initReveal, initScrollProgress } from "@/lib/scroll";
import { registerTourPage } from "@/lib/tour-page";

document.documentElement.classList.add("js");

Alpine.plugin(collapse);
registerHome(Alpine);
registerInquiry(Alpine);
registerTourPage(Alpine);
window.Alpine = Alpine;
Alpine.start();

initReveal();
initScrollProgress();
