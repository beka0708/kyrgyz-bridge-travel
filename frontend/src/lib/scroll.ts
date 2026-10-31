const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Fade blocks in as they enter the screen (`data-reveal`). */
export function initReveal() {
  const items = document.querySelectorAll<HTMLElement>("[data-reveal]");
  if (reducedMotion() || !("IntersectionObserver" in window)) {
    items.forEach((el) => el.classList.add("is-visible"));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      // Items entering together (a row of cards) appear one after another, 50ms apart.
      entries
        .filter((entry) => entry.isIntersecting)
        .forEach((entry, i) => {
          const el = entry.target as HTMLElement;
          if (i > 0) {
            el.style.transitionDelay = `${Math.min(i, 3) * 50}ms`;
            // drop the delay afterwards so hover/press transitions are not delayed
            el.addEventListener("transitionend", () => (el.style.transitionDelay = ""), { once: true });
          }
          el.classList.add("is-visible");
          observer.unobserve(el);
        });
    },
    { rootMargin: "0px 0px -10% 0px" },
  );
  items.forEach((el) => observer.observe(el));
}

/** Thin progress line at the right edge (`data-scroll-progress` holds the bar). */
export function initScrollProgress() {
  const bar = document.querySelector<HTMLElement>("[data-scroll-progress]");
  if (!bar) return;
  let ticking = false;
  const update = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const progress = max > 0 ? Math.min(1, window.scrollY / max) : 0;
    bar.style.transform = `scaleY(${Math.max(progress, 0.04)})`;
    ticking = false;
  };
  window.addEventListener(
    "scroll",
    () => {
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(update);
      }
    },
    { passive: true },
  );
  update();
}
