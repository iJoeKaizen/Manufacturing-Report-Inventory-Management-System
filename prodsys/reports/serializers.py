from rest_framework import serializers
from .models import ProductionReport
from production.models import Machine, Section
from production.serializers import MachineSerializer, SectionSerializer


class ProductionReportSerializer(serializers.ModelSerializer):
    net_output = serializers.ReadOnlyField()
    efficiency = serializers.ReadOnlyField()
    
    # Use nested serializers for read
    machine = MachineSerializer(read_only=True)
    section = SectionSerializer(read_only=True)
    
    # IDs for write
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
        # Attach logged-in user
        user = self.context["request"].user
        validated_data["user"] = user
        return super().create(validated_data)
