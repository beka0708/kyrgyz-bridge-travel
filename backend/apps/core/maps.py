from django.conf import settings

from .models import SiteSettings


def map_config() -> dict:
    """Map providers for the frontend islands (site and admin) and the public API."""
    cfg = settings.MAP
    return {
        "style_url": cfg["STYLE_URL"],
        "topo": {"tiles": cfg["TOPO_TILES"], "attribution": cfg["TOPO_ATTRIBUTION"]},
        "terrain": {
            "tiles": cfg["TERRAIN_TILES"],
            "encoding": cfg["TERRAIN_ENCODING"],
            "attribution": cfg["TERRAIN_ATTRIBUTION"],
        },
        "terrain_3d": SiteSettings.load().map_3d_mode,
    }
