import requests
from django.shortcuts import render

from .models import Noticia
from .services import fetch_pagina, guardar_noticias


def inicio(request):
    """Página única: scrapea las noticias más recientes del CFNA en cada visita."""
    aviso = ""
    try:
        items = fetch_pagina(1)
        guardar_noticias(items)
    except requests.RequestException:
        items = []
        aviso = "No se pudo consultar cfna.org.ar; se muestran las últimas noticias guardadas."
    if items:
        noticias = Noticia.objects.filter(wp_id__in=[i["wp_id"] for i in items])
    else:
        noticias = Noticia.objects.all()[:12]
    return render(request, "noticias/inicio.html", {"noticias": noticias, "aviso": aviso})
