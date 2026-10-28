// Loaded on every page: styles, Alpine for small interactions, scroll effects.
import "@/styles/main.css";

import Alpine from "alpinejs";

import { initReveal, initScrollProgress } from "@/lib/scroll";
import { registerTourPage } from "@/lib/tour-page";

document.documentElement.classList.add("js");

registerTourPage(Alpine);
window.Alpine = Alpine;
Alpine.start();

initReveal();
initScrollProgress();
