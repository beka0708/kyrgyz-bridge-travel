import type Lenis from "lenis";

/**
 * Inertia scrolling on laptops and desktops (mouse wheel / trackpad), like altermind.com: the page
 * glides to where the wheel sends it instead of jumping in steps. Phones and tablets keep their
 * native scroll (already smooth there), and so does anyone who asked for reduced motion — Lenis
 * is not even downloaded for them (a separate chunk loaded only here).
 *
 * Lenis moves the real window scroll, so every scroll listener and CSS scroll-driven animation
 * keeps working. It steps aside for places that scroll on their own (dialogs, the route map,
 * the phone-code list) and pauses while the menu or the photo viewer locks the page.
 */
let lenis: Lenis | null = null;

/**
 * Bring an element into view the way the page scrolls: through Lenis when it runs (a native smooth
 * scroll would fight it), otherwise the browser's own scrollIntoView.
 */
export function scrollToElement(el: Element | null, block: "start" | "center" | "nearest" = "start") {
  if (!el) return;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!lenis) {
    el.scrollIntoView({ block, behavior: reduce ? "auto" : "smooth" });
    return;
  }
  const rect = el.getBoundingClientRect();
  const vh = window.innerHeight;
  if (block === "nearest" && rect.top >= 80 && rect.bottom <= vh) return; // already visible
  const offset = block === "center" ? -(vh - rect.height) / 2 : -80; // room for the sticky header
  lenis.scrollTo(el as HTMLElement, { offset });
}

export async function initSmoothScroll() {
  const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!finePointer || reduce) return;

  const [{ default: Lenis }] = await Promise.all([import("lenis"), import("lenis/dist/lenis.css")]);
  lenis = new Lenis({
    autoRaf: true,
    lerp: 0.085, // lower = longer, softer glide
    wheelMultiplier: 0.9,
    anchors: { offset: -80 }, // same room for the sticky header as scroll-padding-top
    prevent: (node) =>
      node.closest("dialog, [data-lenis-prevent], .maplibregl-map, .iti__country-list") !== null,
  });

  // Pause while something holds the page still: the menu and the photo viewer set
  // `overflow: hidden` on <html>; a modal dialog (guide details) must not let the page glide behind.
  const root = document.documentElement;
  const sync = () => {
    const locked = root.style.overflow === "hidden" || document.querySelector("dialog[open]");
    if (locked) lenis?.stop();
    else lenis?.start();
  };
  const observer = new MutationObserver(sync);
  observer.observe(root, { attributes: true, attributeFilter: ["style"] }); // <html> only
  observer.observe(document.body, { attributes: true, attributeFilter: ["open"], subtree: true });
}
