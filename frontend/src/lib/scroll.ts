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

/**
 * Hero headline (`data-split`): wrap every word in a mask so the words can rise one after another.
 * Keeps inner elements (the orange accent span) and their classes.
 */
export function initSplitHeadings() {
  document.querySelectorAll<HTMLElement>("[data-split]").forEach((el) => {
    let index = 0;
    const wrapWords = (node: Node) => {
      for (const child of Array.from(node.childNodes)) {
        if (child.nodeType === Node.ELEMENT_NODE) {
          wrapWords(child);
          continue;
        }
        if (child.nodeType !== Node.TEXT_NODE || !child.textContent?.trim()) continue;
        const fragment = document.createDocumentFragment();
        for (const part of child.textContent.split(/(\s+)/)) {
          if (!part) continue;
          if (/^\s+$/.test(part)) {
            fragment.append(" ");
            continue;
          }
          const mask = document.createElement("span");
          mask.className = "w";
          const word = document.createElement("span");
          word.style.setProperty("--i", String(index++));
          word.textContent = part;
          mask.append(word);
          fragment.append(mask);
        }
        child.replaceWith(fragment);
      }
    };
    el.setAttribute("aria-label", el.textContent?.replace(/\s+/g, " ").trim() ?? "");
    wrapWords(el);
    el.classList.add("is-split");
  });
}

/** Section titles reveal from a mask; marked here so templates stay clean. */
export function markTitles() {
  document.querySelectorAll<HTMLElement>("main h2.h-section").forEach((el) => {
    if (!el.closest("[data-reveal]")) el.dataset.reveal = "title";
  });
}

/** Photos fade in when loaded. Images already in the cache (or the hero) are left alone. */
export function initImageFade() {
  document.querySelectorAll<HTMLImageElement>(".pic img:not([fetchpriority])").forEach((img) => {
    if (img.complete) return;
    img.classList.add("img-loading");
    const done = () => {
      img.classList.add("img-loaded");
      img.classList.remove("img-loading");
    };
    img.addEventListener("load", done, { once: true });
    img.addEventListener("error", done, { once: true });
  });
}
