from django.db import models


class Noticia(models.Model):
    wp_id = models.PositiveIntegerField("ID en CFNA", unique=True)
    titulo = models.CharField("título", max_length=500)
    url = models.URLField("URL", max_length=500, unique=True)
    imagen_url = models.URLField("imagen", max_length=500, blank=True)
    resumen = models.TextField("resumen", blank=True)
    fecha = models.DateField("fecha de publicación", null=True, blank=True)
    categorias = models.JSONField("categorías", default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"
        ordering = ["-fecha", "-wp_id"]

    def __str__(self):
        return self.titulo


class ScrapeRun(models.Model):
    class Origen(models.TextChoices):
        CRON = "cron", "Automático (timer)"
        API = "api", "API"
        MANUAL = "manual", "Manual"

    class Estado(models.TextChoices):
        OK = "ok", "OK"
        ERROR = "error", "Error"

    origen = models.CharField("origen", max_length=10, choices=Origen.choices, default=Origen.MANUAL)
    paginas = models.PositiveSmallIntegerField("páginas", default=1)
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.OK)
    creadas = models.PositiveIntegerField(default=0)
    actualizadas = models.PositiveIntegerField(default=0)
    error = models.TextField("error", blank=True)
    inicio = models.DateTimeField(auto_now_add=True)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ejecución de scraping"
        verbose_name_plural = "Ejecuciones de scraping"
        ordering = ["-inicio"]

    def __str__(self):
        return f"Scraping #{self.pk} ({self.origen}) — {self.estado}"
