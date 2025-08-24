import django_filters
from .models import ProductionReport


class ProductionReportFilter(django_filters.FilterSet):
    approved = django_filters.BooleanFilter(method="filter_approved")
    date = django_filters.DateFromToRangeFilter(field_name="created_at")

    class Meta:
        model = ProductionReport
        fields = ["status", "machine", "section", "job_number"]

    def filter_approved(self, queryset, name, value):
        if value:
            return queryset.filter(status=ProductionReport.Status.APPROVED)
        return queryset.exclude(status=ProductionReport.Status.APPROVED)
