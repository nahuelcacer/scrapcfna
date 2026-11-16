import os
from datetime import date
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings

from noticias.services import fetch_pagina, parse_articulos, parse_fecha

HTML = """
<article id="post-10685" class="et_pb_post post-10685">
  <a href="https://x/foropla/" class="entry-featured-image-url"><img src="https://x/img.jpg"></a>
  <h2 class="entry-title"><a href="https://x/foropla/"> FORO PLA </a></h2>
  <p class="post-meta"><span class="published">Ene 6, 2026</span> |
    <a href="https://x/category/noticias/" rel="category tag">Noticias</a></p>
  <div class="post-content"><div class="post-content-inner"><p>Resumen</p></div></div>
</article>
"""


class ParseTests(TestCase):
    def test_parse_fecha_en_espanol_e_ingles(self):
        self.assertEqual(parse_fecha("Ene 6, 2026"), date(2026, 1, 6))
        self.assertEqual(parse_fecha("Sep 30, 2026"), date(2026, 9, 30))
        self.assertIsNone(parse_fecha("basura"))

    def test_parse_articulos(self):
        (item,) = parse_articulos(HTML)
        self.assertEqual(item["wp_id"], 10685)
        self.assertEqual(item["titulo"], "FORO PLA")
        self.assertEqual(item["categorias"], ["Noticias"])
        self.assertEqual(item["fecha"], date(2026, 1, 6))


LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM)
class ApiTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("noticias.views.fetch_pagina", side_effect=lambda n: parse_articulos(HTML))
    def test_devuelve_noticias_en_json(self, fetch):
        response = self.client.get("/api/v1/noticias/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], 10685)
        self.assertEqual(data["results"][0]["fecha"], "2026-01-06")
        fetch.assert_called_once_with(1)

    @patch("noticias.views.fetch_pagina", side_effect=requests.ConnectionError())
    def test_502_si_falla_el_scraping(self, _):
        self.assertEqual(self.client.get("/api/v1/noticias/").status_code, 502)

    @patch("noticias.views.fetch_pagina", side_effect=lambda n: parse_articulos(HTML))
    def test_cachea_el_scraping(self, fetch):
        self.client.get("/api/v1/noticias/")
        self.client.get("/api/v1/noticias/")
        fetch.assert_called_once_with(1)

    def test_usa_la_ultima_copia_si_el_sitio_falla(self):
        with patch("noticias.views.fetch_pagina", side_effect=lambda n: parse_articulos(HTML)):
            self.client.get("/api/v1/noticias/")
        cache.delete("noticias:recientes")  # simula que venció el caché
        with patch("noticias.views.fetch_pagina", side_effect=requests.ConnectionError()):
            response = self.client.get("/api/v1/noticias/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)


@override_settings(CACHES=LOCMEM)
class LimiteTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("noticias.views.fetch_pagina", return_value=[])
    def test_limita_a_30_por_minuto(self, _):
        codes = [self.client.get("/api/v1/noticias/").status_code for _ in range(31)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30], 429)


class VerifySslTests(TestCase):
    def _fetch(self):
        with patch("noticias.services.requests.get") as get:
            get.return_value.status_code = 200
            get.return_value.text = HTML
            fetch_pagina(1)
        return get.call_args.kwargs["verify"]

    def test_verifica_ssl_por_defecto(self):
        self.assertIs(self._fetch(), True)

    @override_settings(SCRAPE_VERIFY_SSL=False)
    def test_puede_desactivar_la_verificacion(self):
        self.assertIs(self._fetch(), False)


class EnvBoolTests(TestCase):
    def test_interpreta_la_variable_de_verificacion_ssl(self):
        from config.settings import env_bool

        casos = {"0": False, "false": False, "no": False, "1": True, "true": True}
        for valor, esperado in casos.items():
            with patch.dict(os.environ, {"DJANGO_SCRAPE_VERIFY_SSL": valor}):
                self.assertIs(env_bool("DJANGO_SCRAPE_VERIFY_SSL", True), esperado, valor)

    def test_sin_variable_verifica_por_defecto(self):
        from config.settings import env_bool

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DJANGO_SCRAPE_VERIFY_SSL", None)
            self.assertIs(env_bool("DJANGO_SCRAPE_VERIFY_SSL", True), True)
