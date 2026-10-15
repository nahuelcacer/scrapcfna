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

