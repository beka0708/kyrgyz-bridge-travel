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


const numberFormat = new Intl.NumberFormat("en-US");

/** Count one number up from 0 (`data-count="3000"`); the suffix stays in the markup. */
function countUp(el: HTMLElement, delay = 0) {
  if (el.dataset.counted) return;
  el.dataset.counted = "1";
  const target = Number(el.dataset.count) || 0;
  const duration = 1600;
  let start = 0;
  const tick = (now: number) => {
    start ||= now + delay;
    const t = Math.max(0, Math.min(1, (now - start) / duration));
    const eased = 1 - Math.pow(1 - t, 4); // strong ease-out: fast start, gentle landing
    el.textContent = numberFormat.format(Math.round(target * eased));
    if (t < 1) requestAnimationFrame(tick);
  };
  el.textContent = "0";
  requestAnimationFrame(tick);
}

/** Stats count up when they appear. Numbers in the About block are started by it. */
export function initCounters() {
  const items = Array.from(document.querySelectorAll<HTMLElement>("[data-count]")).filter(
    (el) => !el.closest("[data-about-scene]"),
  );
  if (!items.length || reducedMotion() || !("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        countUp(entry.target as HTMLElement);
      }
    },
    { threshold: 0.6 },
  );
  items.forEach((el) => observer.observe(el));
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** Run `update` on scroll/resize, but only while `section` is near the screen. */
function whileNear(section: HTMLElement, update: () => void) {
  let frame = 0;
  const onScroll = () => (frame ||= requestAnimationFrame(() => ((frame = 0), update())));
  new IntersectionObserver(
    ([entry]) => {
      const method = entry.isIntersecting ? "addEventListener" : "removeEventListener";
      window[method]("scroll", onScroll, { passive: true });
      window[method]("resize", onScroll, { passive: true });
      update();
    },
    { rootMargin: "100px 0px" },
  ).observe(section);
  update();
}

/** Wrap every word of `el` (keeping inner spans such as the accent) for a word-by-word rise. */
function splitWords(el: HTMLElement) {
  let index = 0;
  const walk = (node: Node) => {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === Node.ELEMENT_NODE) {
        walk(child);
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
  walk(el);
}

/**
 * G «floating»: photos drift past the text at their own speeds. The scroll position is followed
 * with inertia (--lp eases towards it each frame), which gives the soft «glide» of altermind.com
 * without taking over the page scroll. The heading rises word by word, then the numbers count.
 */
function initFloating(section: HTMLElement) {
  const title = section.querySelector<HTMLElement>("[data-words]");
  if (title) splitWords(title);
  const counters = Array.from(section.querySelectorAll<HTMLElement>("[data-count]"));
  counters.forEach((el) => (el.textContent = "0"));

  let target = 0;
  let current = 0;
  let loop = 0;
  const read = () => {
    const rect = section.getBoundingClientRect();
    const vh = window.innerHeight;
    // -0.5 when the block enters at the bottom, +0.5 when it leaves at the top
    target = clamp01((vh - rect.top) / (rect.height + vh)) - 0.5;
  };
  const tick = () => {
    current += (target - current) * 0.075;
    section.style.setProperty("--lp", current.toFixed(4));
    loop = Math.abs(target - current) > 0.0005 ? requestAnimationFrame(tick) : 0;
  };
  const update = () => {
    read();
    loop ||= requestAnimationFrame(tick);
  };

  read();
  current = target;
  section.style.setProperty("--lp", current.toFixed(4));
  whileNear(section, update);

  new IntersectionObserver(
    ([entry], observer) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      section.classList.add("is-in");
      counters.forEach((el, i) => countUp(el, 500 + i * 120));
    },
    { threshold: 0.35 },
  ).observe(section.querySelector(".about-float__copy") ?? section);
}

/**
 * About «floating gallery» (`data-about-scene`, templates/partials/about/floating.html): photos
 * drift past the text at their own speeds; see initFloating.
 */
export function initAboutScenes() {
  const section = document.querySelector<HTMLElement>("[data-about-scene]");
  if (!section || reducedMotion() || !("IntersectionObserver" in window)) return;
  section.classList.add("is-scene");
  initFloating(section);
}

/** «How it works» (`data-steps`): play the entrance once, when the steps come into view. */
export function initSteps() {
  const list = document.querySelector<HTMLElement>("[data-steps]");
  if (!list) return;
  if (reducedMotion() || !("IntersectionObserver" in window)) return;
  list.classList.add("is-armed");
  new IntersectionObserver(
    ([entry], observer) => {
      if (!entry.isIntersecting) return;
      observer.disconnect();
      list.classList.add("is-in");
      window.setTimeout(() => list.classList.add("is-done"), 1800); // hover may react now
    },
    { threshold: 0.3 },
  ).observe(list);
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
