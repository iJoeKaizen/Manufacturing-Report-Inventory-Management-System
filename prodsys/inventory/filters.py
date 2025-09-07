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
        search_val = value
        qs = queryset
        qs = qs.filter(
            Q(code__icontains=search_val) | Q(description__icontains=search_val)
        )
        return qs

    def filter_low_stock(self, queryset, name, value: bool):
        qs = queryset
        if value is True:
            qs = qs.filter(quantity__lte=F("reorder_level"))
        else:
            qs = qs
        return qs


class StockMovementFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    movement_type = django_filters.CharFilter(field_name="movement_type", lookup_expr="iexact")
    item_code = django_filters.CharFilter(field_name="item__code", lookup_expr="icontains")
    date_from = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")

    class Meta:
        model = StockMovement
        fields = ["movement_type", "item", "item_code", "date_from", "date_to"]

    def filter_search(self, queryset, name, value):
        search_val = value
        qs = queryset
        qs = qs.filter(
            Q(item__code__icontains=search_val)
            | Q(reference__icontains=search_val)
            | Q(remarks__icontains=search_val)
        )
        return qs
