import type { Iti } from "intl-tel-input";

/** Phone fields with a searchable country list (flags, dial codes, as-you-type format, validation). */
export type PhoneInput = HTMLInputElement & { iti?: Iti };

// Tourists come mostly from these countries: shown at the top of the list.
const TOP_COUNTRIES = ["us", "gb", "de", "fr", "nl", "it", "es", "kg", "kz", "ru"];

/** «de-DE» → «de»; the browser language is a decent first guess of the visitor's country. */
function guessCountry(): string {
  for (const lang of navigator.languages ?? [navigator.language]) {
    const region = lang.split("-")[1];
    if (region && region.length === 2) return region.toLowerCase();
  }
  return "us";
}

async function setup(input: PhoneInput) {
  if (input.iti) return;
  const [{ default: intlTelInput }] = await Promise.all([
    import("intl-tel-input"),
    import("intl-tel-input/styles"),
  ]);
  const guess = guessCountry();
  const known = intlTelInput.getAllCountries().some((country) => country.iso2 === guess);
  input.iti = intlTelInput(input, {
    initialCountry: (known ? guess : "us") as never,
    countryOrder: TOP_COUNTRIES as never,
    countrySearch: true,
    separateDialCode: true,
    strictMode: true,
    formatAsYouType: true,
    containerClass: "w-full",
    loadUtils: () => import("intl-tel-input/utils"),
  });
}

/** Load the widget once a phone field is close to the screen, or right away if it gets focus. */
export function initPhoneInputs() {
  const inputs = document.querySelectorAll<PhoneInput>("input[data-phone]");
  if (!inputs.length) return;
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        void setup(entry.target as PhoneInput);
      }
    },
    { rootMargin: "400px 0px" },
  );
  inputs.forEach((input) => {
    observer.observe(input);
    input.addEventListener("focus", () => void setup(input), { once: true });
  });
}

/**
 * The number in international format (+996704313147) and whether it is valid.
 * Without the widget (not loaded yet) the raw value is returned and trusted to the server.
 */
export function readPhone(input: PhoneInput | null): { value: string; valid: boolean } {
  if (!input) return { value: "", valid: true };
  const raw = input.value.trim();
  if (!raw) return { value: "", valid: true };
  const iti = input.iti;
  if (!iti) return { value: raw, valid: true };
  return { value: iti.getNumber() || raw, valid: iti.isValidNumber() !== false };
}
