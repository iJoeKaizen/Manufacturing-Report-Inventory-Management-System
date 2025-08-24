# reports/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.core.files.uploadedfile import InMemoryUploadedFile
import csv, io
from .models import ProductionReport
from .serializers import ProductionReportSerializer
from .filters import ProductionReportFilter
from inventory.models import Machine
from rest_framework.views import APIView


class ProductionReportViewSet(viewsets.ModelViewSet):
    queryset = ProductionReport.objects.select_related("machine", "section", "user").all()
    serializer_class = ProductionReportSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductionReportFilter
    search_fields = ["job_number"]
    ordering_fields = ["created_at", "quantity_produced", "status"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        machine = serializer.validated_data.get("machine")
        section = serializer.validated_data.get("section")
        
        if machine and not section:
            serializer.save(section=machine.section) 
        else:
            serializer.save()

    def perform_update(self, serializer):
        machine = serializer.validated_data.get("machine")
        section = serializer.validated_data.get("section")

        if machine and not section:
            serializer.save(section=machine.section)
        else:
            serializer.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        report = self.get_object()
        report.status = "approved"
        report.save()
        return Response({"status": "approved"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        """Export all production reports to CSV"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="production_reports.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Job Number", "Product Name", "Quantity Produced", "Waste",
            "Downtime (mins)", "Status", "Section", "Machine", "Created By", "Created At"
        ])

        for report in self.queryset:
            writer.writerow([
                report.job_number,
                getattr(report, "product_name", ""),
                report.quantity_produced,
                report.waste,
                report.downtime_minutes,
                report.status,
                report.section.name if report.section else "",
                report.machine.name if report.machine else "",
                report.user.username if report.user else "",
                report.created_at,
            ])

        return response

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        """Bulk import production reports from uploaded CSV"""
        file_obj: InMemoryUploadedFile = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        decoded_file = file_obj.read().decode("utf-8")
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        created_reports = []
        errors = []

        for idx, row in enumerate(reader, start=1):
            try:
                # Find machine by name
                machine_name = row.get("Machine")
                if not machine_name:
                    raise ValueError("Machine name is required")
                machine = Machine.objects.get(name=machine_name)
                section = machine.section

                report_data = {
                    "job_number": row.get("Job Number"),
                    "quantity_produced": int(row.get("Quantity Produced", 0) or 0),
                    "waste": float(row.get("Waste", 0) or 0),
                    "downtime_minutes": int(row.get("Downtime (mins)", 0) or 0),
                    "status": row.get("Status", "DRAFT").upper(),
                    "machine": machine.id,
                    "section": section.id if section else None,
                    "remarks": row.get("Remarks", ""),
                }

                serializer = self.get_serializer(data=report_data)
                serializer.is_valid(raise_exception=True)
                serializer.save(user=request.user)  # Attach the user here

                created_reports.append(serializer.data)

            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return Response(
            {"created": created_reports, "errors": errors},
            status=status.HTTP_201_CREATED if created_reports else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def download_csv_template(self, request):
        """Download a CSV template with headers for bulk import"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="production_report_template.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Job Number",
            # "Product Name",
            "Quantity Produced",
            "Waste",
            "Downtime (mins)",
            "Status",
            "Machine",
            "Remarks"
        ])
        return response
    
# @api_view(["GET"])
# def reports_root(request):
#     reports = ProductionReport.objects.all()
#     serializer = ProductionReportSerializer(reports, many=True)
#     return Response(serializer.data)

class ReportsRootView(APIView):
    """
    Custom root view for /api/reports/
    Shows router links and optionally first N production reports
    """
    def get(self, request, format=None):
        # Router links
        links = {
            "production-reports": request.build_absolute_uri("/api/reports/production-reports/"),
        }
        
        # Optional: include some production reports (latest 10)
        reports = ProductionReport.objects.order_by("-created_at")[:10]
        serializer = ProductionReportSerializer(reports, many=True)
        
        return Response({
            "links": links,
            "latest_reports": serializer.data
        })