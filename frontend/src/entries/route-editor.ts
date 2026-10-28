import RouteEditor from "@/components/RouteEditor.vue";
import { mountIslands } from "@/lib/islands";

mountIslands("route-editor", RouteEditor, (el) => ({
  input: document.getElementById(el.dataset.inputId!) as HTMLTextAreaElement,
}));
