import type { Alpine as AlpineType } from "alpinejs";

const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign"] as const;
const UTM_STORAGE = "kt-utm";

/** Remember where the visitor came from (first touch of the session) for the inquiry. */
function rememberUtm(): Record<string, string> {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = Object.fromEntries(
    UTM_KEYS.filter((key) => params.get(key)).map((key) => [key, params.get(key)!.slice(0, 100)]),
  );
  try {
    if (Object.keys(fromUrl).length) sessionStorage.setItem(UTM_STORAGE, JSON.stringify(fromUrl));
    return JSON.parse(sessionStorage.getItem(UTM_STORAGE) || "{}");
  } catch {
    return fromUrl; // storage disabled (private mode)
  }
}

declare global {
  interface Window {
    turnstile?: { reset: () => void };
  }
}

export function registerInquiry(Alpine: AlpineType) {
  Alpine.data("inquiryForm", (apiUrl: string) => ({
    busy: false,
    sent: false,
    error: "",
    errors: {} as Record<string, string>,

    init() {
      const utm = rememberUtm();
      this.$el.querySelectorAll<HTMLInputElement>("[data-utm]").forEach((input) => {
        input.value = utm[input.dataset.utm!] ?? "";
      });
    },

    async submit(form: HTMLFormElement) {
      this.error = "";
      this.errors = {};
      const data: Record<string, string> = {};
      new FormData(form).forEach((value, key) => {
        if (typeof value === "string") data[key] = value.trim();
      });

      if (!data.name) this.errors.name = "Please tell us your name.";
      if (!/^\S+@\S+\.\S+$/.test(data.email ?? "")) this.errors.email = "Please enter a valid email.";
      if (Object.keys(this.errors).length) return;

      this.busy = true;
      try {
        const response = await fetch(apiUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRFToken": data.csrfmiddlewaretoken ?? "" },
          body: JSON.stringify({
            name: data.name,
            email: data.email,
            contact: data.contact ?? "",
            tour: data.tour || null,
            date_from: data.date_from || null,
            date_to: data.date_to || null,
            people: Number(data.people) || 1,
            comment: data.comment ?? "",
            page_url: data.page_url ?? "",
            utm_source: data.utm_source ?? "",
            utm_medium: data.utm_medium ?? "",
            utm_campaign: data.utm_campaign ?? "",
            website: data.website ?? "",
            turnstile_token: data["cf-turnstile-response"] ?? "",
          }),
        });
        if (response.status === 201) {
          this.sent = true;
          window.dispatchEvent(new CustomEvent("inquiry:sent", { detail: { tour: data.tour || null } }));
          this.$nextTick(() => (this.$refs.thanks as HTMLElement | undefined)?.focus());
          return;
        }
        if (response.status === 429) {
          this.error = "Too many requests from your network. Please message us on WhatsApp instead.";
          return;
        }
        const body = (await response.json().catch(() => ({}))) as Record<string, string[] | string>;
        for (const [key, value] of Object.entries(body)) {
          const message = Array.isArray(value) ? value[0] : value;
          if (key === "turnstile_token" || key === "non_field_errors" || key === "detail") this.error = message;
          else this.errors[key] = message;
        }
        if (!this.error && !Object.keys(this.errors).length) this.error = "Something went wrong. Please try again.";
      } catch {
        this.error = "No connection. Please check your internet and try again.";
      } finally {
        this.busy = false;
        window.turnstile?.reset();
      }
    },
  }));
}
