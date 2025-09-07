from django.db import models, transaction
from inventory.models import InventoryItem

class Section(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Machine(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="machines")
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.section.name})"

class MaterialConsumption(models.Model):
    report = models.ForeignKey("reports.ProductionReport", on_delete=models.CASCADE, related_name="consumptions")
    material = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="consumptions")
    quantity_used = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=50, default="kg")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        with transaction.atomic():
            if is_new:
                if self.material.quantity < self.quantity_used:
                    raise ValueError(f"{self.material.name} stock not enough. Have: {self.material.quantity}, need: {self.quantity_used}")
                self.material.quantity -= self.quantity_used
                self.material.save()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.material.name} - {self.quantity_used}{self.unit}"
