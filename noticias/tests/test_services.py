from datetime import date
from unittest.mock import patch

import requests
from django.core.cache import cache
from django.test import TestCase

from noticias.services import parse_articulos, parse_fecha

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


class ApiTests(TestCase):
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


class LimiteTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("noticias.views.fetch_pagina", return_value=[])
    def test_limita_a_30_por_minuto(self, _):
        codes = [self.client.get("/api/v1/noticias/").status_code for _ in range(31)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30], 429)
