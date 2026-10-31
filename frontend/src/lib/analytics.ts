import type { Alpine as AlpineType } from "alpinejs";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

const CONSENT_KEY = "kt-consent";
const EU_ATLANTIC = ["Atlantic/Reykjavik", "Atlantic/Canary", "Atlantic/Madeira", "Atlantic/Azores", "Atlantic/Faroe"];

function track(event: string, params: Record<string, unknown> = {}) {
  window.gtag?.("event", event, params);
}

function inEuropeanTimeZone(): boolean {
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? "";
  return zone.startsWith("Europe/") || EU_ATLANTIC.includes(zone);
}

function storedConsent(): string | null {
  try {
    return localStorage.getItem(CONSENT_KEY);
  } catch {
    return null;
  }
}

/** GA4 events: messenger clicks, inquiries, tour views. No-op when GA is not configured. */
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

  document.addEventListener("click", (event) => {
    const link = (event.target as Element).closest<HTMLAnchorElement>("a[href]");
    if (!link) return;
    const messenger = link.href.includes("wa.me") ? "whatsapp" : link.href.includes("t.me") ? "telegram" : "";
    if (messenger) track(`${messenger}_click`, { tour, link_text: link.innerText.trim().slice(0, 40) });
  });

  window.addEventListener("inquiry:sent", (event) => {
    track("generate_lead", { tour: (event as CustomEvent<{ tour: string | null }>).detail?.tour ?? tour });
  });
}

/** Cookie banner for visitors in Europe (Consent Mode v2). */
export function registerConsent(Alpine: AlpineType) {
  Alpine.data("cookieBanner", () => ({
    open: false,
    init() {
      if (!storedConsent() && inEuropeanTimeZone()) this.openBanner();
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
