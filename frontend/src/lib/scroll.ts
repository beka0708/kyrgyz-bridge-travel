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
    bar.style.transform = `scaleY(${progress})`;
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


/** Stats count up from 0 when they appear (`data-count="3000"`, suffix stays in the markup). */
export function initCounters() {
  const items = document.querySelectorAll<HTMLElement>("[data-count]");
  if (!items.length || reducedMotion() || !("IntersectionObserver" in window)) return;
  const format = new Intl.NumberFormat("en-US");
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const el = entry.target as HTMLElement;
        observer.unobserve(el);
        const target = Number(el.dataset.count) || 0;
        const start = performance.now();
        const duration = 1400;
        const tick = (now: number) => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - Math.pow(1 - t, 4); // strong ease-out: fast start, gentle landing
          el.textContent = format.format(Math.round(target * eased));
          if (t < 1) requestAnimationFrame(tick);
        };
        el.textContent = "0";
        requestAnimationFrame(tick);
      }
    },
    { threshold: 0.6 },
  );
  items.forEach((el) => observer.observe(el));
}
