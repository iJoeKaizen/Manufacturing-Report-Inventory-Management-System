from django.db import models, transaction
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


# ---------------------------
# Choices for Category & Unit
# ---------------------------
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


# ---------------------------
# Inventory Item
# ---------------------------
class InventoryItem(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, default="unamed item")
    width = models.PositiveSmallIntegerField(blank=True, default=0, help_text="in mm")  # in mm
    length = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="in meter")
    thickness = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,default=0, help_text="in mm")
    gsm = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, default=0, help_text="grams per square meter")
    weight = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="in kg")  # in kg
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

    # ---------------------------
    # Validation
    # ---------------------------
    def clean(self):
        numeric_fields = ["width", "length", "thickness", "gsm", "weight", "quantity", "reorder_level"]
        for field in numeric_fields:
            value = getattr(self, field)
            if value is not None and value < 0:
                raise ValidationError({field: f"{field} cannot be negative"})

    # ---------------------------
    # Stock helper methods
    # ---------------------------
    def is_below_reorder(self):
        return self.quantity <= self.reorder_level

    def recalc_quantity(self):
        """Recalculate quantity from StockMovements (IN, OUT, ADJUST)."""
        in_sum = self.movements.filter(movement_type="IN").aggregate(total=Sum("quantity"))["total"] or 0
        out_sum = self.movements.filter(movement_type="OUT").aggregate(total=Sum("quantity"))["total"] or 0
        adjust_sum = self.movements.filter(movement_type="ADJUST").aggregate(total=Sum("quantity"))["total"] or 0

        self.quantity = in_sum - out_sum + adjust_sum
        self.save(update_fields=["quantity", "last_updated"])
        return self.quantity


# ---------------------------
# Stock Movement
# ---------------------------
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


# ---------------------------
# Bill of Materials (BOM)
# ---------------------------
class BillOfMaterial(models.Model):
    finished_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="bom_lines"
    )
    raw_item = models.ForeignKey(
        InventoryItem, on_delete=models.CASCADE, related_name="used_in_boms"
    )
    quantity_required = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("finished_item", "raw_item")

    def __str__(self):
        return f"{self.finished_item.code} requires {self.quantity_required} {self.raw_item.uom} of {self.raw_item.code}"

    def clean(self):
        if self.quantity_required <= 0:
            raise ValidationError({"quantity_required": "Quantity required must be positive"})


# ---------------------------
# Transactional stock deduction utility
# ---------------------------
def deduct_stock(materials: dict[int, float], reference: str = None, user: User = None):
    """
    Deduct stock for multiple items atomically.
    materials = {item_id: quantity_to_deduct}
    """
    from .models import InventoryItem, StockMovement

    with transaction.atomic():
        for item_id, qty in materials.items():
            if qty <= 0:
                raise ValueError(f"Quantity to deduct must be positive for item {item_id}")

            # Lock row to prevent race conditions
            item = InventoryItem.objects.select_for_update().get(pk=item_id)
            if item.quantity < qty:
                raise ValueError(f"Insufficient stock for {item.code}")

            item.quantity -= qty
            item.save(update_fields=["quantity", "last_updated"])

            StockMovement.objects.create(
                item=item,
                movement_type="OUT",
                quantity=qty,
                reference=reference,
                remarks="Auto-deducted via transaction",
                created_by=user
            )
