from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Section, Machine, MaterialConsumption

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = "__all__"

class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = "__all__"

class MaterialConsumptionSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source="material.name", read_only=True)

    class Meta:
        model = MaterialConsumption
        fields = ["id", "report", "material", "material_name", "quantity_used", "unit", "created_at"]
        read_only_fields = ["id", "created_at", "report", "material_name"]

    def validate(self, data):
        report = data.get("report") or getattr(self.instance, "report", None)
        material = data.get("material") or getattr(self.instance, "material", None)
        quantity = data.get("quantity_used") or getattr(self.instance, "quantity_used", None)

        if report and report.status == "APPROVED":
            raise ValidationError("You can't add or change consumptions for approved reports.")

        if material and quantity is not None:
            if material.quantity < quantity:
                raise ValidationError(f"Not enough stock for {material.name}. Available: {material.quantity}, needed: {quantity}")

        return data
