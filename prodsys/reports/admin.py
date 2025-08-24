from django.contrib import admin
from .models import ProductionReport, ReportAuditTrail, ExportedReport
from inventory.models import Machine, Section

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

    # Remove autocomplete_fields to use normal dropdowns
    # autocomplete_fields = ["machine", "section"]  

    readonly_fields = ["waste", "created_at", "approved_at"]

    # Populate dropdowns with all available machines and sections
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "machine":
            kwargs["queryset"] = Machine.objects.all()
        if db_field.name == "section":
            kwargs["queryset"] = Section.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(ReportAuditTrail)
class ReportAuditTrailAdmin(admin.ModelAdmin):
    list_display = ["report", "changed_by", "change_type", "timestamp"]
    list_filter = ["change_type", "timestamp"]
    search_fields = ["report__job_number", "changed_by__username"]

@admin.register(ExportedReport)
class ExportedReportAdmin(admin.ModelAdmin):
    list_display = ["report", "file_type", "exported_by", "exported_at"]
    list_filter = ["file_type", "exported_at"]
    search_fields = ["report__job_number", "exported_by__username"]
