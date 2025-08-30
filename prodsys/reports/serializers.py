# reports/serializers.py
from rest_framework import serializers
from .models import ProductionReport
from production.models import Machine, Section


class MachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Machine
        fields = ["id", "name"]


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ["id", "name"]


class ProductionReportSerializer(serializers.ModelSerializer):
    net_output = serializers.ReadOnlyField()
    efficiency = serializers.ReadOnlyField()
    machine = MachineSerializer(read_only=True)
    section = SectionSerializer(read_only=True)
    machine_id = serializers.PrimaryKeyRelatedField(
        queryset=Machine.objects.all(), write_only=True, source="machine"
    )
    section_id = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(), write_only=True, source="section"
    )

    class Meta:
        model = ProductionReport
        fields = [
            "id",
            "job_number",
            "machine",
            "machine_id",
            "section",
            "section_id",
            "quantity_produced",
            "waste",
            "downtime_minutes",
            "input_raw_materials",
            "output_products",
            "consumables_used",
            "remarks",
            "status",
            "created_at",
            "net_output",
            "efficiency",
        ]
        read_only_fields = ["created_at", "waste", "net_output", "efficiency"]

    def create(self, validated_data):
        # attach logged-in user
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)