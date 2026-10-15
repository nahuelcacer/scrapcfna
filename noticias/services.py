"""Scraping de https://www.cfna.org.ar/noticias/ (WordPress + Divi)."""
import re
from datetime import date

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from .models import Noticia

MESES = {
    "ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "may": 5,
    "jun": 6, "jul": 7, "ago": 8, "aug": 8, "sep": 9, "set": 9, "oct": 10,
    "nov": 11, "dic": 12, "dec": 12,
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scrapcfna/1.0)"}
TIMEOUT = 20


def parse_fecha(texto):
    """'Sep 30, 2026' / 'Ene 6, 2026' -> date."""
    m = re.match(r"\s*(\w+)\.?\s+(\d{1,2}),\s*(\d{4})", texto or "")
    if not m or m.group(1).lower()[:3] not in MESES:
        return None
    return date(int(m.group(3)), MESES[m.group(1).lower()[:3]], int(m.group(2)))


def parse_articulos(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for art in soup.select("article.et_pb_post"):
        link = art.select_one("h2.entry-title a")
        wp_id = re.search(r"post-(\d+)", art.get("id", ""))
        if not link or not wp_id:
            continue
        img = art.select_one("a.entry-featured-image-url img")
        fecha = art.select_one(".post-meta .published")
        resumen = art.select_one(".post-content-inner")
        items.append({
            "wp_id": int(wp_id.group(1)),
            "titulo": link.get_text(strip=True),
            "url": link["href"],
            "imagen_url": img["src"] if img else "",
            "resumen": resumen.get_text(" ", strip=True) if resumen else "",
            "fecha": parse_fecha(fecha.get_text() if fecha else ""),
            "categorias": [a.get_text(strip=True) for a in art.select(".post-meta a[rel~=tag]")],
        })
    return items


def fetch_pagina(numero):
    base = settings.CFNA_NOTICIAS_URL.rstrip("/")
    url = f"{base}/page/{numero}/?et_blog"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return parse_articulos(resp.text)


def guardar_noticias(items):
    """Upsert de items parseados. Devuelve (creadas, actualizadas)."""
    creadas = actualizadas = 0
    for item in items:
        _, created = Noticia.objects.update_or_create(
            wp_id=item["wp_id"], defaults={k: v for k, v in item.items() if k != "wp_id"}
        )
        creadas += created
        actualizadas += not created
    return creadas, actualizadas

