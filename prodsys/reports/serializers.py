from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import ProductionReport, ReportAuditTrail
from production.models import Machine, Section, MaterialConsumption
from production.serializers import MachineSerializer, SectionSerializer

class ProductionReportSerializer(serializers.ModelSerializer):
    net_output = serializers.ReadOnlyField()
    efficiency = serializers.ReadOnlyField()

    # for reading nested
    machine = MachineSerializer(read_only=True)
    section = SectionSerializer(read_only=True)

    # for writing ids
    machine_id = serializers.PrimaryKeyRelatedField(queryset=Machine.objects.all(), write_only=True, source="machine")
    section_id = serializers.PrimaryKeyRelatedField(queryset=Section.objects.all(), write_only=True, source="section")

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
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.status == ProductionReport.Status.APPROVED:
            raise ValidationError("Cannot modify approved reports")
        return super().update(instance, validated_data)


class MaterialConsumptionSerializer(serializers.ModelSerializer):
    report = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = MaterialConsumption
        fields = ["id", "report", "material", "quantity_used"]

    def validate(self, attrs):
        report = attrs.get("report") or getattr(self.instance, "report", None)
        if report and report.status == ProductionReport.Status.APPROVED:
            raise ValidationError("Cannot modify MaterialConsumption for approved report")
        return attrs


class ReportAuditTrailSerializer(serializers.ModelSerializer):
    report_job_number = serializers.CharField(source="report.job_number", read_only=True)
    changed_by_username = serializers.CharField(source="changed_by.username", read_only=True)

    class Meta:
        model = ReportAuditTrail
        fields = [
            "id",
            "report",
            "report_job_number",
            "changed_by",
            "changed_by_username",
            "change_type",
            "field_name",
            "old_value",
            "new_value",
            "timestamp",
        ]
        read_only_fields = fields


# optional stock movement serializer
try:
    from inventory.models import StockMovement
except Exception:
    StockMovement = None

if StockMovement:
    class StockMovementSerializer(serializers.ModelSerializer):
        item_name = serializers.CharField(source="item.name", read_only=True)

        class Meta:
            model = StockMovement
            fields = [
                "id",
                "item",
                "item_name",
                "movement_type",
                "quantity",
                "reference",
                "remarks",
                "created_at",
            ]
            read_only_fields = fields
else:
    class StockMovementSerializer(serializers.Serializer):
        pass
