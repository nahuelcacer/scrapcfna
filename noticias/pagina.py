import requests
from django.http import JsonResponse
from django.shortcuts import render

from .models import Noticia
from .services import fetch_pagina, guardar_noticias


def _noticias_recientes():
    """Scrapea la portada de noticias del CFNA; si falla, usa lo guardado. Devuelve (noticias, error)."""
    try:
        items = fetch_pagina(1)
        guardar_noticias(items)
    except requests.RequestException:
        return Noticia.objects.all()[:12], True
    return Noticia.objects.filter(wp_id__in=[i["wp_id"] for i in items]), False


def inicio(request):
    """Página única: scrapea las noticias más recientes del CFNA en cada visita."""
    noticias, error = _noticias_recientes()
    aviso = "No se pudo consultar cfna.org.ar; se muestran las últimas noticias guardadas." if error else ""
    return render(request, "noticias/inicio.html", {"noticias": noticias, "aviso": aviso})


def noticias_json(request):
    """Mismas noticias que la página, en JSON, para que las consuma otro servidor."""
    noticias, error = _noticias_recientes()
    return JsonResponse(
        {
            "actualizado": not error,
            "count": len(noticias),
            "results": [
                {
                    "id": n.wp_id,
                    "titulo": n.titulo,
                    "url": n.url,
                    "imagen_url": n.imagen_url,
                    "resumen": n.resumen,
                    "fecha": n.fecha.isoformat() if n.fecha else None,
                    "categorias": n.categorias,
                }
                for n in noticias
            ],
        },
        json_dumps_params={"ensure_ascii": False},
    )
