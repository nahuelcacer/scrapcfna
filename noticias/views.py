import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .filters import NoticiaFilter
from .models import Noticia, ScrapeRun
from .serializers import NoticiaSerializer, ScrapeRequestSerializer, ScrapeRunSerializer
from .services import ejecutar_scraping, fetch_pagina, guardar_noticias


class ScrapingError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "No se pudo obtener las noticias desde cfna.org.ar."
    default_code = "scraping_error"


class NoticiaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Noticia.objects.all()
    serializer_class = NoticiaSerializer
    filterset_class = NoticiaFilter
    search_fields = ["titulo", "resumen"]
    ordering_fields = ["fecha", "titulo"]

    def get_throttles(self):
        if self.action == "page":
            self.throttle_scope = "scrape_page"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_permissions(self):
        if self.action == "scrape":
            return [IsAdminUser()]
        return [AllowAny()]

    @action(detail=False, methods=["post"])
    def scrape(self, request):
        """Dispara el scraping de cfna.org.ar/noticias (solo admin)."""
        params = ScrapeRequestSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        try:
            run = ejecutar_scraping(params.validated_data["paginas"], origen=ScrapeRun.Origen.API)
        except requests.RequestException as exc:
            raise ScrapingError() from exc
        return Response({"creadas": run.creadas, "actualizadas": run.actualizadas})

    def page(self, request, num):
        """Scrapea en vivo cfna.org.ar/noticias/page/<num>/?et_blog, guarda y devuelve las noticias."""
        try:
            items = fetch_pagina(int(num))
        except requests.RequestException as exc:
            raise ScrapingError() from exc
        if not items:
            raise NotFound("Esa página no tiene noticias.")
        guardar_noticias(items)
        noticias = Noticia.objects.filter(wp_id__in=[i["wp_id"] for i in items])
        return Response({
            "page": int(num),
            "count": len(items),
            "results": NoticiaSerializer(noticias, many=True).data,
        })


class ScrapeRunViewSet(viewsets.ReadOnlyModelViewSet):
    """Historial de ejecuciones del scraping (solo admin)."""

    queryset = ScrapeRun.objects.all()
    serializer_class = ScrapeRunSerializer
    filterset_fields = ["estado", "origen"]
