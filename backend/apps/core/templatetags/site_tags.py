import re

from django import template
from django.utils.html import escape, format_html, format_html_join

from apps.core.images import og_image, safe_variants

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


@register.simple_tag
def img(fieldfile, alt="", sizes="100vw", css="", loading="lazy", priority=False):
    """Responsive <img> with a WebP srcset: {% img tour.cover alt=tour.title sizes="50vw" %}"""
    if not fieldfile:
        return ""
    found = safe_variants(fieldfile)
    default = next((v for v in found if v.width >= 960), found[-1])
    attrs = [("src", default.url), ("alt", alt), ("decoding", "async")]
    srcset = ", ".join(f"{v.url} {v.width}w" for v in found if v.width)
    if srcset:
        attrs += [("srcset", srcset), ("sizes", sizes)]
    if css:
        attrs.append(("class", css))
    attrs.append(("fetchpriority", "high") if priority else ("loading", loading))
    return format_html("<img {}>", format_html_join(" ", '{}="{}"', attrs))


@register.simple_tag
def og_image_url(fieldfile):
    """Absolute-path URL of the 1200×630 social preview JPEG ('' when there is no image)."""
    if not fieldfile:
        return ""
    try:
        return og_image(fieldfile)
    except Exception:
        return fieldfile.url


@register.simple_tag
def preload_img(fieldfile, sizes="100vw"):
    """<link rel=preload> for the LCP image, so it starts before CSS and fonts finish."""
    if not fieldfile:
        return ""
    found = [v for v in safe_variants(fieldfile) if v.width]
    if not found:
        return ""
    srcset = ", ".join(f"{v.url} {v.width}w" for v in found)
    return format_html(
        '<link rel="preload" as="image" imagesrcset="{}" imagesizes="{}" fetchpriority="high">',
        srcset,
        sizes,
    )
