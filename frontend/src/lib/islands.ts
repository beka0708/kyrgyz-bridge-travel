import { createApp, type Component } from "vue";

/**
 * Mount a Vue component on every `[data-island="<name>"]` element.
 * Props come from a <script type="application/json"> made by Django's json_script,
 * referenced by `data-props-id`, so the server renders data without extra requests.
 */
export function mountIslands(
  name: string,
  component: Component,
  extraProps: (el: HTMLElement) => Record<string, unknown> = () => ({}),
) {
  document.querySelectorAll<HTMLElement>(`[data-island="${name}"]`).forEach((el) => {
    if (el.dataset.mounted) return;
    const source = el.dataset.propsId ? document.getElementById(el.dataset.propsId) : null;
    const props = source?.textContent ? JSON.parse(source.textContent) : {};
    createApp(component, { ...props, ...extraProps(el) }).mount(el);
    el.dataset.mounted = "true";
  });
}
