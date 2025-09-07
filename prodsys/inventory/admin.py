from django.contrib import admin
from .models import InventoryItem, StockMovement


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "category",
        "quantity",
        "uom",            
        "reorder_level",
        "last_updated",  
    )
    list_filter = ("category",)
    search_fields = ("code", "description")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("item", "movement_type", "quantity", "reference", "timestamp")
    list_filter = ("movement_type", "timestamp")
    search_fields = ("item__code", "reference", "remarks")
