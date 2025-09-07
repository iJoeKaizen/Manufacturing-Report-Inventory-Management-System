from django.db import models, transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class InventoryCategory(models.TextChoices):
    RAW = "RAW", "Raw Material"
    CONSUMABLE = "CONSUMABLE", "Consumable"
    WIP = "WIP", "Work In Progress"
    FINISHED = "FG", "Finished Goods"

class UnitOfMeasure(models.TextChoices):
    KG = "kg", "Kilogram"
    METER = "m", "Meter"
    ROLL = "roll", "Roll"
    SHEET = "sheet", "Sheet"
    LITER = "l", "Liter"
    CARTON = "carton", "Carton"

class InventoryItem(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, default="unamed item")
    width = models.PositiveSmallIntegerField(blank=True, default=0)
    length = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    thickness = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    gsm = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0)
    weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=20, choices=InventoryCategory.choices)
    uom = models.CharField(max_length=20, choices=UnitOfMeasure.choices, default=UnitOfMeasure.KG)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        fields_to_check = ["width", "length", "thickness", "gsm", "weight", "quantity", "reorder_level"]
        for field_name in fields_to_check:
            value = getattr(self, field_name, 0)
            if value is not None and value < 0:
                raise ValidationError({field_name: f"{field_name} cannot be negative"})

    def is_below_reorder(self):
        return self.quantity <= self.reorder_level

    def recalc_quantity(self):
        in_total = self.movements.filter(movement_type="IN").aggregate(total=Sum("quantity"))["total"] or 0
        out_total = self.movements.filter(movement_type="OUT").aggregate(total=Sum("quantity"))["total"] or 0
        adjust_total = self.movements.filter(movement_type="ADJUST").aggregate(total=Sum("quantity"))["total"] or 0
        calculated = in_total - out_total + adjust_total
        self.quantity = calculated
        self.save(update_fields=["quantity", "last_updated"])
        return self.quantity

class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("ADJUST", "Adjustment"),
        ("TRANSFER", "Transfer"),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.movement_type} - {self.item.code} ({self.quantity})"

class MaterialRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    stock_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    po_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.status == "APPROVED":
            if self.stock_item.quantity < self.po_quantity:
                raise ValidationError({
                    "po_quantity": f"Insufficient stock for {self.stock_item.code}. Available: {self.stock_item.quantity}, Required: {self.po_quantity}"
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        new_approval = False
        if self.pk:
            original = MaterialRequest.objects.get(pk=self.pk)
            if original.status != "APPROVED" and self.status == "APPROVED":
                new_approval = True
        else:
            if self.status == "APPROVED":
                new_approval = True

        super().save(*args, **kwargs)

        if new_approval:
            deduct_stock(
                {self.stock_item.id: self.po_quantity},
                reference=f"MaterialRequest-{self.id}",
                user=self.requested_by
            )

    def __str__(self):
        return f"{self.stock_item.code} ({self.po_quantity}) - {self.status}"

class BillOfMaterial(models.Model):
    finished_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="bom_lines")
    raw_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="used_in_boms")
    quantity_required = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("finished_item", "raw_item")

    def __str__(self):
        return f"{self.finished_item.code} requires {self.quantity_required} {self.raw_item.uom} of {self.raw_item.code}"

    def clean(self):
        if self.quantity_required <= 0:
            raise ValidationError({"quantity_required": "Quantity required must be positive"})

def deduct_stock(materials: dict[int, float], reference: str = None, user: User = None):
    from .models import InventoryItem, StockMovement
    with transaction.atomic():
        for item_id, qty in materials.items():
            if qty <= 0:
                raise ValueError(f"Quantity must be positive for item {item_id}")

            item = InventoryItem.objects.select_for_update().get(pk=item_id)
            if item.quantity < qty:
                raise ValueError(f"Insufficient stock for {item.code}")

            new_qty = item.quantity - qty
            item.quantity = new_qty
            item.save(update_fields=["quantity", "last_updated"])

            StockMovement.objects.create(
                item=item,
                movement_type="OUT",
                quantity=qty,
                reference=reference,
                remarks="Auto-deducted via transaction",
                created_by=user
            )
