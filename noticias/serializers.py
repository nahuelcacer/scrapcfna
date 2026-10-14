from rest_framework import serializers

from .models import Noticia, ScrapeRun


class NoticiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Noticia
        fields = ["id", "wp_id", "titulo", "url", "imagen_url", "resumen", "fecha", "categorias"]
        read_only_fields = fields


class ScrapeRequestSerializer(serializers.Serializer):
    paginas = serializers.IntegerField(min_value=1, max_value=50, default=1)


class ScrapeRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapeRun
        fields = ["id", "origen", "paginas", "estado", "creadas", "actualizadas", "error", "inicio", "fin"]
        read_only_fields = fields
