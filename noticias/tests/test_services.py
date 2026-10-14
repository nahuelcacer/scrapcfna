from datetime import date
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from noticias.models import Noticia
from noticias.services import parse_articulos, parse_fecha, scrapear_noticias

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


class ScrapeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("noticias.services.fetch_pagina")
    def test_scrape_es_idempotente(self, fetch):
        fetch.side_effect = lambda n: parse_articulos(HTML) if n == 1 else []
        self.assertEqual(scrapear_noticias(3), (1, 0))
        self.assertEqual(scrapear_noticias(3), (0, 1))
        self.assertEqual(Noticia.objects.count(), 1)

    def test_listado_es_publico(self):
        self.assertEqual(self.client.get("/api/v1/noticias/").status_code, status.HTTP_200_OK)

    def test_scrape_requiere_admin(self):
        response = self.client.post("/api/v1/noticias/scrape/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class PageThrottleTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @patch("noticias.views.fetch_pagina", return_value=[])
    def test_page_limita_a_10_por_minuto(self, _):
        client = APIClient()
        codes = [client.get("/api/v1/noticias/page/1").status_code for _ in range(11)]
        self.assertEqual(codes[:10], [status.HTTP_404_NOT_FOUND] * 10)
        self.assertEqual(codes[10], status.HTTP_429_TOO_MANY_REQUESTS)
