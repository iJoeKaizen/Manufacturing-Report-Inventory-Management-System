from django.contrib import admin
from .models import ProductionReport, ReportAuditTrail, ExportedReport
# from inventory.models import Machine, Section

@admin.register(ProductionReport)
class ProductionReportAdmin(admin.ModelAdmin):
    list_display = [
        "job_number",
        "machine",
        "section",
        "quantity_produced",
        "waste",
        "downtime_minutes",
        "status",
        "created_at",
        "approved_at",
    ]
    list_filter = ["status", "created_at", "machine", "section"]
    search_fields = ["job_number", "remarks"]

    readonly_fields = ["waste", "created_at", "approved_at"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Populate dropdowns with all available machines and sections instead of autocomplete"""
        if db_field.name == "machine":
            kwargs["queryset"] = Machine.objects.all()
        if db_field.name == "section":
            kwargs["queryset"] = Section.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        """Optimize queryset with related fields"""
        return super().get_queryset(request).select_related("machine", "section")


@admin.register(ReportAuditTrail)
class ReportAuditTrailAdmin(admin.ModelAdmin):
    list_display = ["report", "changed_by", "change_type", "timestamp"]
    list_filter = ["change_type", "timestamp"]
    search_fields = ["report__job_number", "changed_by__username"]
    raw_id_fields = ["report", "changed_by"]  # faster lookups if you have thousands of rows


@admin.register(ExportedReport)
class ExportedReportAdmin(admin.ModelAdmin):
    list_display = ["report", "file_type", "exported_by", "exported_at"]
    list_filter = ["file_type", "exported_at"]
    search_fields = ["report__job_number", "exported_by__username"]
    raw_id_fields = ["report", "exported_by"]
