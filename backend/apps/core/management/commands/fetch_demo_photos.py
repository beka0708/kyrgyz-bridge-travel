"""Download the demo photo set listed in demo/photos.json through the official Unsplash API.

Needs a free Unsplash developer key: https://unsplash.com/oauth/applications → New Application →
copy the «Access Key» into .env as UNSPLASH_ACCESS_KEY. Files go to demo/photos/<key>.jpg (not in
git); re-running skips existing files. Follows the API guidelines: hotlink `urls.raw` with a
width and trigger `links.download_location` for every download.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

DEMO_DIR = Path(settings.DEMO_DIR)
MANIFEST = DEMO_DIR / "photos.json"
PHOTOS_DIR = DEMO_DIR / "photos"
API = "https://api.unsplash.com"

# People and avatars are shown small; landscapes may fill a wide screen; the hero and the footer
# band are full-width on large retina screens.
PORTRAIT_PREFIXES = ("guide-", "review-")
FULL_BLEED = ("hero", "footer", "about", "founder")


def _get(url: str, key: str, as_json: bool = True):
    request = urllib.request.Request(
        url, headers={"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}
    )
    with urllib.request.urlopen(request, timeout=60) as resp:
        data = resp.read()
    return json.loads(data) if as_json else data


class Command(BaseCommand):
    help = (
        "Download demo photos via the Unsplash API into demo/photos/ (needs UNSPLASH_ACCESS_KEY)."
    )

    def handle(self, *args, **options):
        key = getattr(settings, "UNSPLASH_ACCESS_KEY", "")
        if not key:
            raise CommandError(
                "Set UNSPLASH_ACCESS_KEY in .env (free: https://unsplash.com/oauth/applications)."
            )
        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        photos = json.loads(MANIFEST.read_text(encoding="utf-8"))["photos"]
        meta_cache: dict[str, dict] = {}
        done = failed = 0
        for name, item in photos.items():
            target = PHOTOS_DIR / f"{name}.jpg"
            if target.exists():
                done += 1
                continue
            uid = item.get("unsplash_id")
            if not uid:  # a photo from the client: copied into demo/photos/ by hand
                failed += 1
                self.stderr.write(f"  {name}: client photo missing, copy it to {target}")
                continue
            width = 900 if name.startswith(PORTRAIT_PREFIXES) else 2000
            if name in FULL_BLEED:
                width = 3200
            try:
                meta = meta_cache.get(uid) or _get(f"{API}/photos/{uid}", key)
                meta_cache[uid] = meta
                raw = meta["urls"]["raw"]
                sep = "&" if "?" in raw else "?"
                image_url = f"{raw}{sep}" + urllib.parse.urlencode(
                    {"w": width, "q": 88 if name in FULL_BLEED else 82, "fm": "jpg", "fit": "max"}
                )
                with urllib.request.urlopen(image_url, timeout=60) as resp:
                    target.write_bytes(resp.read())
                with Image.open(target) as im:
                    im.verify()
                # Unsplash API guideline: register the download with the photographer's stats.
                _get(meta["links"]["download_location"], key)
            except Exception as exc:  # noqa: BLE001 - report and continue with the rest
                target.unlink(missing_ok=True)
                failed += 1
                self.stderr.write(f"  {name} ({uid}): {exc}")
                continue
            done += 1
            self.stdout.write(f"  {name}")
            time.sleep(0.2)
        self.stdout.write(self.style.SUCCESS(f"Photos ready: {done}, failed: {failed}"))
        if failed:
            self.stdout.write(
                "Demo-mode keys allow 50 requests/hour: run again later for the rest."
            )
