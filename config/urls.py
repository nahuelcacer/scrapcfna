from django.urls import path

from noticias.views import NoticiasRecientes

urlpatterns = [
    path("api/v1/noticias/", NoticiasRecientes.as_view(), name="noticias"),
]
