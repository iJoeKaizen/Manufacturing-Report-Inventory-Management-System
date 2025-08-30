from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from inventory.models import (
    StockMovement,
    InventoryItem,
    BillOfMaterial,
)
from reports.models import ProductionReport, MaterialConsumption


# --- Auto update InventoryItem.quantity when StockMovement created ---
@receiver(post_save, sender=StockMovement)
def update_inventory_quantity(sender, instance, created, **kwargs):
    if not created:
        return

    item = instance.item
    if instance.movement_type == "IN":
        item.quantity += instance.quantity
    elif instance.movement_type == "OUT":
        item.quantity -= instance.quantity
    elif instance.movement_type == "ADJUST":
        item.quantity = instance.quantity
    # TRANSFER handled separately
    item.save(update_fields=["quantity"])


# --- Handle ProductionReport approval ---
@receiver(post_save, sender=ProductionReport)
def handle_production_report(sender, instance, created, **kwargs):
    """
    When a ProductionReport is approved:
      1. Create MaterialConsumption rows for raw materials
      2. Create StockMovement (OUT) for raw materials
      3. Create StockMovement (IN) for finished goods
    Entire operation is atomic: either all succeed or all rollback.
    """
    if not instance.approved:
        return

    with transaction.atomic():
        # --- 1. Create MaterialConsumption + Stock OUT for raw materials ---
        bom_lines = BillOfMaterial.objects.filter(finished_item=instance.product)
        for line in bom_lines:
            qty_required = line.quantity_required * instance.quantity

            consumption, created_mc = MaterialConsumption.objects.get_or_create(
                report=instance,
                raw_item=line.raw_item,
                defaults={"quantity_used": qty_required},
            )

            if created_mc:
                StockMovement.objects.create(
                    item=line.raw_item,
                    movement_type="OUT",
                    quantity=qty_required,
                    reference=f"PR-{instance.id}",
                    remarks="Auto deduction from production consumption",
                )

        # --- 2. Create StockMovement (IN) for finished goods ---
        StockMovement.objects.get_or_create(
            item=instance.product,
            movement_type="IN",
            quantity=instance.quantity,
            reference=f"PR-{instance.id}",
            remarks="Finished goods added from production approval",
        )
