import type { Alpine as AlpineType } from "alpinejs";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

const CONSENT_KEY = "kt-consent";

function track(event: string, params: Record<string, unknown> = {}) {
  window.gtag?.("event", event, params);
}

function storedConsent(): string | null {
  try {
    return localStorage.getItem(CONSENT_KEY);
  } catch {
    return null;
  }
}

/**
 * Our own counter for the admin dashboard: taps on WhatsApp / phone / email links.
 * sendBeacon does not delay opening WhatsApp; no cookies, no personal data.
 */
export function initContactBeacons() {
  document.addEventListener("click", (event) => {
    const link = (event.target as Element).closest<HTMLAnchorElement>("a[href]");
    if (!link) return;
    const href = link.href;
    const channel = href.includes("wa.me")
      ? "whatsapp"
      : href.startsWith("tel:")
        ? "phone"
        : href.startsWith("mailto:")
          ? "email"
          : "";
    if (!channel || !navigator.sendBeacon) return;
    const body = new Blob([JSON.stringify({ channel })], { type: "application/json" });
    navigator.sendBeacon("/api/v1/stats/click/", body);
  });
}

/**
 * GA4 events — the funnel from interest to a request. No-op until a GA ID is set in the admin.
 *   view_item          a tour page was opened (with price)
 *   select_item        a tour card was clicked (home, list, «You may also like»)
 *   filter_tours       a filter chip on the home page
 *   form_start         the visitor started filling the request form
 *   generate_lead      a request was sent              ← mark as a key event in GA
 *   contact_click      WhatsApp / phone / email tapped  ← mark as a key event in GA
 *   review_submitted   a guest review was sent
 */
export function initAnalytics() {
  if (!window.gtag) return;
  const tour = document.body.dataset.tour;

  if (tour) {
    const price = Number(document.body.dataset.tourPrice) || undefined;
    track("view_item", {
      currency: document.body.dataset.tourCurrency,
      value: price,
      items: [{ item_id: tour, item_name: document.body.dataset.tourTitle, price }],
    });
  }
  if (location.pathname.startsWith("/reviews/new/") && new URLSearchParams(location.search).get("sent")) {
    track("review_submitted");
  }

  document.addEventListener("click", (event) => {
    const link = (event.target as Element).closest<HTMLAnchorElement>("a[href]");
    if (!link) return;
    const href = link.href;
    const channel = href.includes("wa.me")
      ? "whatsapp"
      : href.startsWith("tel:")
        ? "phone"
        : href.startsWith("mailto:")
          ? "email"
          : "";
    if (channel) {
      track("contact_click", { channel, tour, link_text: link.innerText.trim().slice(0, 40) });
      return;
    }
    const card = link.closest(".tour-card");
    const slug = link.pathname.match(/^\/tours\/([^/]+)\/$/)?.[1];
    if (card && slug) {
      track("select_item", { item_list_name: location.pathname === "/" ? "home" : location.pathname, items: [{ item_id: slug }] });
    }
  });

  window.addEventListener("tours:filter", (event) => {
    track("filter_tours", { filter: (event as CustomEvent<string>).detail });
  });

  document.addEventListener(
    "focusin",
    (event) => {
      const form = (event.target as Element).closest("#contact form");
      if (form && !form.hasAttribute("data-started")) {
        form.setAttribute("data-started", "");
        track("form_start", { tour });
      }
    },
  );

  window.addEventListener("inquiry:sent", (event) => {
    track("generate_lead", { tour: (event as CustomEvent<{ tour: string | null }>).detail?.tour ?? tour });
  });
}

/** Cookie banner (Consent Mode v2), shown only when a GA ID is set in the admin. */
export function registerConsent(Alpine: AlpineType) {
  // «Cookie settings» buttons (footer, legal pages) work anywhere, inside a component or not.
  document.addEventListener("click", (event) => {
    if ((event.target as Element | null)?.closest("[data-cookie-settings]")) {
      window.dispatchEvent(new Event("cookie-settings"));
    }
  });
  Alpine.data("cookieBanner", () => ({
    open: false,
    init() {
      // Everyone sees it once (only while Google Analytics is on): simpler and safer than
      // guessing the visitor's country. Inside the EEA/UK/CH nothing is stored before «Accept».
      if (!storedConsent()) this.openBanner();
    },
    openBanner() {
      this.open = true;
      // keyboard users land on the choice instead of tabbing through the whole page
      this.$nextTick(() => (this.$refs.first as HTMLElement | undefined)?.focus({ preventScroll: true }));
    },
    choose(choice: "granted" | "denied") {
      try {
        localStorage.setItem(CONSENT_KEY, choice);
      } catch {
        /* private mode: the choice lasts for this page only */
      }
      window.gtag?.("consent", "update", { analytics_storage: choice });
      this.open = false;
      (document.getElementById("top") as HTMLElement | null)?.focus({ preventScroll: true });
    },
  }));
}
