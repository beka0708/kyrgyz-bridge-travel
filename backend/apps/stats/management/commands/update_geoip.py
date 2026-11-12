"""Download the free DB-IP «IP to Country Lite» database (monthly; cron in deploy/crontab.example).

Attribution required by the licence (CC BY 4.0): «IP Geolocation by DB-IP» on the privacy page.
"""

import gzip
import shutil
import tempfile
import urllib.request
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.stats.geo import reset_reader

URL = "https://download.db-ip.com/free/dbip-country-lite-{month}.mmdb.gz"
# an honest name for our downloader (the default «Python-urllib» is refused)
USER_AGENT = "KyrgyzBridgeTravel-update_geoip/1.0 (+https://kyrgyzbridgetravel.com)"


def _months_back(today: date, n: int) -> list[str]:
    months, year, month = [], today.year, today.month
    for _ in range(n):
        months.append(f"{year}-{month:02d}")
        month -= 1
        if not month:
            year, month = year - 1, 12
    return months


class Command(BaseCommand):
    help = "Download the DB-IP country database used for «visitors by country»."

    def add_arguments(self, parser):
        parser.add_argument("--if-missing", action="store_true", help="Only when there is no file.")

    def handle(self, *args, **options):
        target = settings.GEOIP_PATH
        if options["if_missing"] and target.exists():
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        # the new month's file appears during the first days of the month
        for month in _months_back(date.today(), 2):
            url = URL.format(month=month)
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with (
                    urllib.request.urlopen(request, timeout=60) as response,  # noqa: S310
                    tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp,
                    gzip.GzipFile(fileobj=response) as unpacked,
                ):
                    shutil.copyfileobj(unpacked, tmp)
                    tmp_path = tmp.name
            except OSError as exc:
                self.stderr.write(f"{url}: {exc}")
                continue
            shutil.move(tmp_path, target)
            reset_reader()
            self.stdout.write(self.style.SUCCESS(f"GeoIP database {month} saved to {target}"))
            return
        raise CommandError("Could not download the DB-IP database.")
