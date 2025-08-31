from rest_framework import serializers
from .models import InventoryItem, StockMovement


# ---------------------------
# Inventory Item Serializer
# ---------------------------
class InventoryItemSerializer(serializers.ModelSerializer):
    is_below_reorder = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "code",
            "name",
            "width",
            "length",
            "thickness",
            "gsm",
            "weight",
            "description",
            "category",
            "uom",
            "quantity",
            "reorder_level",
            "last_updated",
            "is_below_reorder",
        ]
        read_only_fields = ["id", "last_updated", "is_below_reorder"]

    def get_is_below_reorder(self, obj):
        return obj.is_below_reorder()


# ---------------------------
# Stock Movement Serializer
# ---------------------------
class StockMovementSerializer(serializers.ModelSerializer):
    item_detail = InventoryItemSerializer(source="item", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "item",
            "item_detail",
            "movement_type",
            "quantity",
            "reference",
            "remarks",
            "timestamp",
            "created_by",
        ]
        read_only_fields = ["id", "timestamp", "created_by"]


# ---------------------------
# Stock Action Serializers
# ---------------------------
class StockBaseActionSerializer(serializers.Serializer):
    """Base serializer for stock actions (for consistency)."""
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class StockInSerializer(StockBaseActionSerializer):
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)


class StockOutSerializer(StockBaseActionSerializer):
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_quantity(self, value):
        item = self.context.get("item")
        if item and item.quantity < value:
            raise serializers.ValidationError("Insufficient stock for this operation.")
        return value


class StockAdjustSerializer(StockBaseActionSerializer):
    delta = serializers.DecimalField(max_digits=12, decimal_places=2)


class StockTransferSerializer(StockBaseActionSerializer):
    to_item_id = serializers.PrimaryKeyRelatedField(
        queryset=InventoryItem.objects.all(), source="to_item"
    )
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_quantity(self, value):
        item = self.context.get("item")
        if item and item.quantity < value:
            raise serializers.ValidationError("Insufficient stock for this operation.")
        return value
