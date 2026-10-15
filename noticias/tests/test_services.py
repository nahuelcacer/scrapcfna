from datetime import date
from unittest.mock import patch

import requests
from django.test import TestCase

from noticias.models import Noticia
from noticias.services import guardar_noticias, parse_articulos, parse_fecha

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


class GuardarTests(TestCase):
    def test_guardar_es_idempotente(self):
        items = parse_articulos(HTML)
        self.assertEqual(guardar_noticias(items), (1, 0))
        self.assertEqual(guardar_noticias(items), (0, 1))
        self.assertEqual(Noticia.objects.count(), 1)


class JsonTests(TestCase):
    @patch("noticias.pagina.fetch_pagina", side_effect=lambda n: parse_articulos(HTML))
    def test_json_devuelve_noticias(self, _):
        data = self.client.get("/noticias.json").json()
        self.assertTrue(data["actualizado"])
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["titulo"], "FORO PLA")
        self.assertEqual(data["results"][0]["fecha"], "2026-01-06")

    @patch("noticias.pagina.fetch_pagina", side_effect=requests.ConnectionError())
    def test_json_usa_guardadas_si_falla(self, _):
        guardar_noticias(parse_articulos(HTML))
        data = self.client.get("/noticias.json").json()
        self.assertFalse(data["actualizado"])
        self.assertEqual(data["count"], 1)
