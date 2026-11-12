/**
 * Magnetic buttons, for a real mouse only (phones and reduced motion get none): the main buttons
 * lean towards the cursor and spring back. `translate` only; nothing runs while the mouse is still.
 */
const fine = () =>
  window.matchMedia("(hover: hover) and (pointer: fine)").matches &&
  !window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const MAGNETIC = ".btn-accent, .btn-wa, .social-btn, [data-magnetic]";

export function initMagnetic() {
  if (!fine()) return;
  document.querySelectorAll<HTMLElement>(MAGNETIC).forEach((el) => {
    el.classList.add("is-magnetic");
    const strength = el.classList.contains("social-btn") ? 0.35 : 0.22;
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - (r.left + r.width / 2)) * strength;
      const y = (e.clientY - (r.top + r.height / 2)) * strength;
      el.style.translate = `${x.toFixed(1)}px ${y.toFixed(1)}px`;
    });
    el.addEventListener("pointerleave", () => (el.style.translate = ""));
  });
}
