from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from noticias.models import ScrapeRun
from noticias.services import ejecutar_scraping, parse_articulos
from noticias.tests.test_services import HTML


class EjecutarScrapingTests(TestCase):
    @patch("noticias.services.fetch_pagina")
    def test_registra_ejecucion_ok(self, fetch):
        fetch.side_effect = lambda n: parse_articulos(HTML) if n == 1 else []
        run = ejecutar_scraping(2, origen="cron")
        self.assertEqual((run.estado, run.creadas, run.actualizadas), ("ok", 1, 0))
        self.assertEqual(run.origen, "cron")
        self.assertIsNotNone(run.fin)

    @patch("noticias.services.fetch_pagina", side_effect=requests.ConnectionError("sin red"))
    def test_registra_error_y_propaga(self, _):
        with self.assertRaises(requests.ConnectionError):
            ejecutar_scraping(1, origen="cron")
        run = ScrapeRun.objects.get()
        self.assertEqual(run.estado, "error")
        self.assertIn("sin red", run.error)
        self.assertIsNotNone(run.fin)

    @patch("noticias.services.fetch_pagina", side_effect=requests.ConnectionError("sin red"))
    def test_comando_falla_con_command_error(self, _):
        with self.assertRaises(CommandError):
            call_command("scrapear_noticias", "--origen", "cron")


class ScrapeRunsApiTests(TestCase):
    def test_requiere_admin(self):
        response = APIClient().get("/api/v1/scrape-runs/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_admin_puede_listar(self):
        admin = get_user_model().objects.create_superuser("admin", password="x")
        client = APIClient()
        client.force_authenticate(admin)
        ScrapeRun.objects.create(origen="cron")
        response = client.get("/api/v1/scrape-runs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
