import requests
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


class NoticiasRecientes(APIView):
    """Scrapea la primera página de cfna.org.ar/noticias en cada petición y la devuelve."""

    def get(self, request):
        try:
            items = fetch_pagina(1)
        except requests.RequestException as exc:
            raise ScrapingError() from exc
        return Response({"count": len(items), "results": NoticiaSerializer(items, many=True).data})
