from django_filters import rest_framework as filters

from .models import Noticia


class NoticiaFilter(filters.FilterSet):
    desde = filters.DateFilter(field_name="fecha", lookup_expr="gte")
    hasta = filters.DateFilter(field_name="fecha", lookup_expr="lte")
    categoria = filters.CharFilter(field_name="categorias", lookup_expr="icontains")

    class Meta:
        model = Noticia
        fields = ["desde", "hasta", "categoria"]
