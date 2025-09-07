from django.db.models.signals import post_save, pre_delete, pre_save
from django.db.models import F
from django.dispatch import receiver
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from decimal import Decimal
from rest_framework import serializers

from reports.models import ProductionReport, ReportAuditTrail
from production.models import MaterialConsumption
from inventory.models import InventoryItem, StockMovement, UnitOfMeasure, InventoryCategory, BillOfMaterial

# some constants
COMPLETED_STATES = {"completed", "COMPLETED", "approved", "APPROVED"}
CHANGE_TYPES = ReportAuditTrail.ChangeType

# helper functions
def log_audit(report, user, change_type):
    ReportAuditTrail.objects.create(
        report=report,
        changed_by=user,
        change_type=change_type,
        timestamp=now(),
    )

def validate_stock_for_approval(report):
    bom_lines = BillOfMaterial.objects.filter(finished_item=report.product)
    for line in bom_lines:
        qty_required = line.quantity_required * report.quantity_produced
        if line.raw_item.quantity < qty_required:
            raise ValidationError(
                f"Cannot approve report. Raw material {line.raw_item.name} not enough. Required {qty_required}, Available {line.raw_item.quantity}"
            )

# signals
@receiver(pre_save, sender=ProductionReport)
def pre_save_production_report(sender, instance, **kwargs):
    if instance.pk:
        old_instance = ProductionReport.objects.filter(pk=instance.pk).first()
        if old_instance and old_instance.status != instance.status:
            if instance.status in {"APPROVED", "approved"}:
                validate_stock_for_approval(instance)

@receiver(post_save, sender=ProductionReport)
def handle_production_report(sender, instance, created, **kwargs):
    user = getattr(instance, "_changed_by", None)

    if created:
        log_audit(instance, user, CHANGE_TYPES.CREATE)
        return

    if instance.status in COMPLETED_STATES:
        # remove raw materials
        for line in instance.materials_consumed.all():
            StockMovement.objects.create(
                item=line.raw_item,
                movement_type="OUT",
                quantity=line.quantity_used,
                reference=f"Report {instance.id}",
                remarks="Auto-deducted by production",
            )
            InventoryItem.objects.filter(pk=line.raw_item.pk).update(
                quantity=F("quantity") - line.quantity_used
            )

        # add finished goods
        product_sku = instance.product_name or instance.job_number
        finished_qty = instance.quantity or instance.quantity_produced

        if product_sku and finished_qty:
            finished_item, _ = InventoryItem.objects.get_or_create(
                item_code=product_sku,
                defaults=dict(
                    category=InventoryCategory.FINISHED,
                    description=f"Finished goods for {product_sku}",
                    unit_of_measure=UnitOfMeasure.CARTON,
                    quantity=Decimal("0"),
                    reorder_level=Decimal("0"),
                ),
            )
            InventoryItem.objects.filter(pk=finished_item.pk).update(
                quantity=F("quantity") + Decimal(finished_qty)
            )
            StockMovement.objects.create(
                item=finished_item,
                movement_type="IN",
                quantity=Decimal(finished_qty),
                reference=f"Report {instance.id}",
                remarks="Auto: production completed",
            )

        log_audit(instance, user, CHANGE_TYPES.APPROVAL)

@receiver(pre_delete, sender=ProductionReport)
def log_report_delete(sender, instance, using, **kwargs):
    user = getattr(instance, "_deleted_by", None)
    log_audit(instance, user, CHANGE_TYPES.DELETE)

# serializer
class ReportAuditTrailSerializer(serializers.ModelSerializer):
    report_job_number = serializers.CharField(source="report.job_number", read_only=True)
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)

    class Meta:
        model = ReportAuditTrail
        fields = [
            "id",
            "report",
            "report_job_number",
            "changed_by",
            "changed_by_username",
            "change_type",
            "timestamp",
        ]
        read_only_fields = fields
