import requests
from django.core.management.base import BaseCommand, CommandError

from noticias.models import ScrapeRun
from noticias.services import ejecutar_scraping


class Command(BaseCommand):
    help = "Scrapea las noticias de cfna.org.ar"

    def add_arguments(self, parser):
        parser.add_argument("--paginas", type=int, default=1)
        parser.add_argument("--origen", choices=ScrapeRun.Origen.values, default=ScrapeRun.Origen.MANUAL)

    def handle(self, *args, **opts):
        try:
            run = ejecutar_scraping(opts["paginas"], origen=opts["origen"])
        except requests.RequestException as exc:
            raise CommandError(f"Falló el scraping: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Creadas: {run.creadas} · Actualizadas: {run.actualizadas}"))
