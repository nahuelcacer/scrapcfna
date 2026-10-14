from django.contrib import admin

from .models import Noticia, ScrapeRun


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "fecha", "wp_id"]
    search_fields = ["titulo"]


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = ["inicio", "origen", "estado", "paginas", "creadas", "actualizadas"]
    list_filter = ["estado", "origen"]
