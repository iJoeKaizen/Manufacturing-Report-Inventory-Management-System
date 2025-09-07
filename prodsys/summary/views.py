from django.db.models import Sum, Avg, F, ExpressionWrapper, FloatField
from rest_framework.response import Response
from rest_framework.views import APIView
from reports.models import ProductionReport

class SummaryView(APIView):
    def get(self, request):
        reports = ProductionReport.objects.all()

        total_input = reports.aggregate(total=Sum("input_raw_materials"))["total"] or 0
        total_output = reports.aggregate(total=Sum("output_products"))["total"] or 0
        total_consumables = reports.aggregate(total=Sum("consumables_used"))["total"] or 0
        total_waste = reports.aggregate(total=Sum("waste"))["total"] or 0

        avg_efficiency = (
            reports.annotate(
                efficiency=ExpressionWrapper(
                    (F("output_products") * 100.0) / F("input_raw_materials"),
                    output_field=FloatField(),
                )
            ).aggregate(avg_eff=Avg("efficiency"))["avg_eff"]
            or 0
        )

        data = {
            "total_input": float(total_input),
            "total_output": float(total_output),
            "total_consumables": float(total_consumables),
            "total_waste": float(total_waste),
            "average_efficiency": round(avg_efficiency, 2),
        }
        return Response(data)
