from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from inventory.models import StockMovement, InventoryItem, BillOfMaterial, MaterialRequest, deduct_stock
from reports.models import ProductionReport
from production.models import MaterialConsumption


@receiver(post_save, sender=StockMovement)
def update_inventory(sender, instance, created, **kwargs):
    if not created:
        return
    stock_item = instance.item
    qty = instance.quantity
    if instance.movement_type == "IN":
        stock_item.quantity += qty
    elif instance.movement_type == "OUT":
        stock_item.quantity -= qty
    elif instance.movement_type == "ADJUST":
        stock_item.quantity = qty
    stock_item.save(update_fields=["quantity"])


@receiver(pre_save, sender=MaterialRequest)
def track_material_request_old_status(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.filter(pk=instance.pk).first()
        instance._old_status = old.status if old else None
    else:
        instance._old_status = None


@receiver(pre_save, sender=ProductionReport)
def track_production_report_old_status(sender, instance, **kwargs):
    if instance.pk:
        old = sender.objects.filter(pk=instance.pk).first()
        instance._old_status = old.status if old else None
    else:
        instance._old_status = None


@receiver(post_save, sender=ProductionReport)
def handle_production_report_approval(sender, instance, created, **kwargs):
    if created:
        return
    old_status = instance._old_status
    new_status = instance.status
    if old_status == "PENDING" and new_status == "APPROVED":
        bom_lines = BillOfMaterial.objects.filter(finished_item=instance.product)
        for line in bom_lines:
            raw_item = line.raw_item
            total_needed = line.quantity_required * instance.quantity_produced
            MaterialConsumption.objects.create(
                report=instance,
                raw_item=raw_item,
                quantity_used=total_needed
            )
            StockMovement.objects.create(
                item=raw_item,
                movement_type="OUT",
                quantity=total_needed,
                reference="PR-" + str(instance.id),
                remarks="Deduct raw material for production"
            )
        StockMovement.objects.create(
            item=instance.product,
            movement_type="IN",
            quantity=instance.quantity_produced,
            reference="PR-" + str(instance.id),
            remarks="Add finished product to stock"
        )


@receiver(post_save, sender=MaterialRequest)
def handle_material_request(sender, instance, created, **kwargs):
    if created:
        return
    old_status = instance._old_status
    new_status = instance.status
    item = instance.stock_item
    qty = instance.po_quantity
    if old_status == "PENDING" and new_status == "APPROVED":
        if item.quantity < qty:
            raise ValidationError(
                f"Not enough stock for {item.code}. Available: {item.quantity}, Required: {qty}"
            )
        deduct_stock({item.id: qty}, reference="MaterialRequest-" + str(instance.id), user=instance.requested_by)
        StockMovement.objects.create(
            item=item,
            movement_type="OUT",
            quantity=qty,
            reference="MR-" + str(instance.id),
            remarks="Deduct stock for approved request"
        )
    elif old_status == "APPROVED" and new_status == "CANCELLED":
        StockMovement.objects.create(
            item=item,
            movement_type="IN",
            quantity=qty,
            reference="MR-" + str(instance.id) + "-CANCEL",
            remarks="Add stock back because request was cancelled"
        )
