import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NoticiaSerializer
from .services import fetch_pagina


class ScrapingError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "No se pudo obtener las noticias desde cfna.org.ar."
    default_code = "scraping_error"


CACHE_KEY = "noticias:recientes"
CACHE_KEY_RESPALDO = "noticias:recientes:respaldo"
RESPALDO_TTL = 60 * 60 * 24


class NoticiasRecientes(APIView):
    """Scrapea la primera página de cfna.org.ar/noticias y la cachea unos minutos.

    Si el sitio falla, responde con la última copia buena (hasta 24 h) en vez de un 502.
    """

    def get(self, request):
        data = cache.get(CACHE_KEY)
        if data is None:
            try:
                items = fetch_pagina(1)
            except requests.RequestException as exc:
                data = cache.get(CACHE_KEY_RESPALDO)
                if data is None:
                    raise ScrapingError() from exc
            else:
                data = {"count": len(items), "results": NoticiaSerializer(items, many=True).data}
                cache.set(CACHE_KEY, data, settings.NOTICIAS_CACHE_SEGUNDOS)
                cache.set(CACHE_KEY_RESPALDO, data, RESPALDO_TTL)
        response = Response(data)
        response["Cache-Control"] = f"public, max-age={settings.NOTICIAS_CACHE_SEGUNDOS}"
        return response
