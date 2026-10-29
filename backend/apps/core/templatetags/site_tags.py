import re

from django import template
from django.utils.html import escape, format_html

register = template.Library()


@register.filter
def accent_title(title, css_class="text-accent"):
    """Colour part of a heading like the mockups.

    «Mountains, lakes *and yurts*» -> Mountains, lakes <span>and yurts</span> (explicit, from admin)
    «Ala-Kul: hike to the lake» -> Ala-Kul: <span>hike to the lake</span>
    «Song-Kul Nights» -> Song-Kul <span>Nights</span>
    """
    css_class = css_class or "text-accent"
    title = str(title or "")
    starred = re.fullmatch(r"(.*?)\*(.+?)\*(.*)", title, flags=re.S)
    if starred:
        head, accent, tail = starred.groups()
        return format_html('{}<span class="{}">{}</span>{}', head, css_class, accent, tail)
    if ":" in title:
        head, tail = title.split(":", 1)
        head, tail = f"{head}:", tail.strip()
    elif " " in title.strip():
        head, tail = title.strip().rsplit(" ", 1)
    else:
        return escape(title)
    return format_html('{} <span class="{}">{}</span>', head, css_class, tail)


@register.simple_tag
def inquiry_tours():
    """Published tours for the «Which tour?» select of the inquiry form."""
    from apps.tours.models import Tour

    return Tour.objects.published().only("title", "slug")
