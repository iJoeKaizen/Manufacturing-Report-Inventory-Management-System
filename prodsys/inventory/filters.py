import django_filters
from django.db.models import Q, F
from .models import InventoryItem, StockMovement


class InventoryItemFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    category = django_filters.CharFilter(field_name="category", lookup_expr="iexact")
    supplier = django_filters.CharFilter(field_name="supplier", lookup_expr="icontains")
    low_stock = django_filters.BooleanFilter(method="filter_low_stock")

    class Meta:
        model = InventoryItem
        fields = ["category", "supplier"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(item_code__icontains=value) | Q(description__icontains=value)
        )

    def filter_low_stock(self, queryset, name, value: bool):
        if value:
            return queryset.filter(quantity__lte=F("reorder_level"))
        return queryset


class StockMovementFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    movement_type = django_filters.CharFilter(field_name="movement_type", lookup_expr="iexact")
    item_code = django_filters.CharFilter(field_name="item__item_code", lookup_expr="icontains")
    date_from = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = StockMovement
        fields = ["movement_type", "item", "item_code", "date_from", "date_to"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(item__item_code__icontains=value)
            | Q(reference__icontains=value)
            | Q(remarks__icontains=value)
        )
