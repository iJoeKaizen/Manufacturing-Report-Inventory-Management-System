from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from decimal import Decimal

from reports.models import (
    ProductionReport,
    MaterialConsumption,
    ReportAuditTrail,
)
from inventory.models import (
    InventoryItem,
    StockMovement,
    UnitOfMeasure,
    InventoryCategory,
    BillOfMaterial,
)

COMPLETED_STATES = {"completed", "APPROVED"}  # support both naming schemes


# ------------------------
# Inventory stock updates
# ------------------------

@receiver(post_save, sender=ProductionReport)
def on_report_completed(sender, instance: ProductionReport, created, **kwargs):
    status_val = getattr(instance, "status", None)
    if status_val not in COMPLETED_STATES:
        return

    product_sku = getattr(instance, "product_name", None) or getattr(instance, "job_number", None)
    finished_qty = getattr(instance, "quantity", None) or getattr(instance, "quantity_produced", None)

    if product_sku and finished_qty:
        item, _ = InventoryItem.objects.get_or_create(
            item_code=product_sku,
            defaults=dict(
                category=InventoryCategory.FINISHED,
                description=f"Finished goods for {product_sku}",
                unit_of_measure=UnitOfMeasure.CARTON,
                quantity_available=Decimal("0"),
                reorder_level=Decimal("0"),
            ),
        )
        item.quantity_available = (item.quantity_available or Decimal("0")) + Decimal(finished_qty)
        item.save(update_fields=["quantity_available", "last_updated"])
        StockMovement.objects.create(
            item=item,
            movement_type="IN",
            quantity=Decimal(finished_qty),
            reference=getattr(instance, "job_id", None) or getattr(instance, "job_number", None),
            remarks="Auto: production completed",
        )


@receiver(post_save, sender=ProductionReport)
def handle_production_inventory(sender, instance, created, **kwargs):
    if instance.status not in COMPLETED_STATES:
        return

    # Deduct raw
    for line in instance.materials_consumed.all():
        StockMovement.objects.create(
            item=line.raw_item,
            movement_type="OUT",
            quantity=line.quantity_used,
            reference=f"Report {instance.id}",
            remarks="Auto-deducted by production"
        )
        line.raw_item.quantity -= line.quantity_used
        line.raw_item.save()

    # Add FG
    if instance.finished_item and instance.output_quantity:
        StockMovement.objects.create(
            item=instance.finished_item,
            movement_type="IN",
            quantity=instance.output_quantity,
            reference=f"Report {instance.id}",
            remarks="Auto-added by production"
        )
        instance.finished_item.quantity += instance.output_quantity
        instance.finished_item.save()


@receiver(post_save, sender=ProductionReport)
def create_stock_movements_on_approval(sender, instance, created, **kwargs):
    if instance.status != "APPROVED":
        return

    for consumption in instance.materials_consumed.all():
        StockMovement.objects.get_or_create(
            item=consumption.raw_item,
            movement_type="OUT",
            quantity=consumption.quantity_used,
            reference=f"Report {instance.id}",
            defaults={"remarks": "Auto-deducted via report approval"},
        )


def check_stock_before_approval(sender, instance, **kwargs):
    if instance.approved:
        bom_lines = BillOfMaterial.objects.filter(finished_item=instance.product)

        for line in bom_lines:
            qty_required = line.quantity_required * instance.quantity_produced
            if line.raw_item.quantity < qty_required:
                raise ValidationError(
                    f"Cannot approve report. "
                    f"Raw material {line.raw_item.name} insufficient. "
                    f"Required {qty_required}, Available {line.raw_item.quantity}"
                )


# ------------------------
# Audit Trail logging
# ------------------------

@receiver(pre_delete, sender=ProductionReport)
def log_report_delete(sender, instance, using, **kwargs):
    """
    Log DELETE in ReportAuditTrail when a ProductionReport is deleted.
    This works for deletes in API, Admin, or shell.
    """
    ReportAuditTrail.objects.create(
        report=instance,
        changed_by=getattr(instance, "_deleted_by", None),  # set in view if available
        change_type=ReportAuditTrail.ChangeType.DELETE,
        timestamp=now(),
    )
