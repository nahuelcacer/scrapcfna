from rest_framework import serializers


class NoticiaSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="wp_id")
    titulo = serializers.CharField()
    url = serializers.URLField()
    imagen_url = serializers.CharField(allow_blank=True)
    resumen = serializers.CharField(allow_blank=True)
    fecha = serializers.DateField(allow_null=True)
    categorias = serializers.ListField(child=serializers.CharField())
