from django.db import models
from django.conf import settings
from inventory.models import InventoryItem
from production.models import Machine, Section

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class ProductionReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    machine = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="reports")
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="reports")
    finished_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, default=1)

    job_number = models.CharField(max_length=50, db_index=True)
    quantity_produced = models.IntegerField(default=0)
    downtime_minutes = models.IntegerField(default=0)

    input_raw_materials = models.DecimalField(max_digits=10, decimal_places=2)
    output_products = models.DecimalField(max_digits=10, decimal_places=2)
    consumables_used = models.DecimalField(max_digits=10, decimal_places=2)
    waste = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    estimated_input = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_output = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        indexes = [
            models.Index(fields=["job_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            orig = ProductionReport.all_objects.get(pk=self.pk)
            if orig.status == self.Status.APPROVED:
                raise ValueError("Approved reports cannot be changed")

        if self.input_raw_materials is not None and self.output_products is not None:
            self.waste = self.input_raw_materials - self.output_products

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status == self.Status.APPROVED:
            raise ValueError("Cannot delete approved report")
        self.is_deleted = True
        self.save()

    @property
    def net_output(self):
        return self.output_products - self.waste

    @property
    def efficiency(self):
        if self.input_raw_materials:
            return round((self.output_products / self.input_raw_materials) * 100, 2)
        return 0

    def __str__(self):
        return f"{self.job_number} ({self.status})"


class ReportAuditTrail(models.Model):
    class ChangeType(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        APPROVE = "APPROVE", "Approve"
        CONSUMPTION_CREATE = "CONSUMPTION_CREATE", "Consumption Created"
        CONSUMPTION_UPDATE = "CONSUMPTION_UPDATE", "Consumption Updated"
        CONSUMPTION_DELETE = "CONSUMPTION_DELETE", "Consumption Deleted"

    report = models.ForeignKey(ProductionReport, on_delete=models.CASCADE, related_name="audit_trails")
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    change_type = models.CharField(max_length=50, choices=ChangeType.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)


class ExportedReport(models.Model):
    class FileType(models.TextChoices):
        PDF = "PDF", "PDF"
        EXCEL = "EXCEL", "Excel"

    report = models.ForeignKey(ProductionReport, on_delete=models.CASCADE, related_name="exports")
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    exported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    exported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report.job_number} exported as {self.file_type}"
