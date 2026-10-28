from django import template
from django.utils.html import escape, format_html

register = template.Library()


@register.filter
def accent_title(title, css_class="text-accent"):
    """Colour the second part of a heading like the mockups: after a colon, else the last word.

    «Ala-Kul: hike to the lake» -> Ala-Kul: <span>hike to the lake</span>
    «Song-Kul Nights» -> Song-Kul <span>Nights</span>
    """
    title = str(title or "")
    if ":" in title:
        head, tail = title.split(":", 1)
        head, tail = f"{head}:", tail.strip()
    elif " " in title.strip():
        head, tail = title.strip().rsplit(" ", 1)
    else:
        return escape(title)
    return format_html('{} <span class="{}">{}</span>', head, css_class, tail)
