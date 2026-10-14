from django.urls import re_path
from rest_framework.routers import DefaultRouter

from .views import NoticiaViewSet, ScrapeRunViewSet

router = DefaultRouter()
router.register("noticias", NoticiaViewSet, basename="noticia")
router.register("scrape-runs", ScrapeRunViewSet, basename="scrape-run")

urlpatterns = [
    re_path(r"^noticias/page/(?P<num>\d+)/?$", NoticiaViewSet.as_view({"get": "page"}), name="noticia-page"),
] + router.urls
