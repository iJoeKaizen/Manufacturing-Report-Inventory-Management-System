import csv, io, uuid
from django.utils.timezone import now
from django.db import transaction
from django.core.cache import cache
from django.http import HttpResponse
from django.core.files.uploadedfile import InMemoryUploadedFile

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import ReportPermission
from .models import ProductionReport, ReportAuditTrail
from .serializers import ProductionReportSerializer
from .filters import ProductionReportFilter
from production.models import Machine


class ProductionReportViewSet(viewsets.ModelViewSet):
    queryset = ProductionReport.objects.select_related("machine", "section", "user").all()
    serializer_class = ProductionReportSerializer
    permission_classes = [IsAuthenticated, ReportPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductionReportFilter
    search_fields = ["job_number"]
    ordering_fields = ["created_at", "quantity_produced", "status"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        """Save new report and log CREATE audit trail"""
        machine = serializer.validated_data.get("machine")
        section = serializer.validated_data.get("section")

        if machine and not section:
            report = serializer.save(user=self.request.user, section=machine.section)
        else:
            report = serializer.save(user=self.request.user)

        ReportAuditTrail.objects.create(
            report=report,
            changed_by=self.request.user,
            change_type=ReportAuditTrail.ChangeType.CREATE
        )

    def perform_update(self, serializer):
        """Update report and log UPDATE audit trail"""
        machine = serializer.validated_data.get("machine")
        section = serializer.validated_data.get("section")

        if machine and not section:
            report = serializer.save(section=machine.section)
        else:
            report = serializer.save()

        ReportAuditTrail.objects.create(
            report=report,
            changed_by=self.request.user,
            change_type=ReportAuditTrail.ChangeType.UPDATE
        )

    def destroy(self, request, *args, **kwargs):
        """Log a DELETE audit entry before removing the report"""
        report = self.get_object()
        try:
            with transaction.atomic():
                ReportAuditTrail.objects.create(
                    report=report,
                    changed_by=request.user,
                    change_type=ReportAuditTrail.ChangeType.DELETE
                )
                return super().destroy(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a report and log audit"""
        report = self.get_object()

        if report.status == ProductionReport.Status.APPROVED:
            return Response({"detail": "Report is already approved."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                report.status = ProductionReport.Status.APPROVED
                report.approved_at = now()
                report.save()

                ReportAuditTrail.objects.create(
                    report=report,
                    changed_by=request.user,
                    change_type=ReportAuditTrail.ChangeType.APPROVE
                )
            return Response({"status": "approved"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        """Export all production reports to CSV (with filters applied)"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="production_reports.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Job Number", "Product Name", "Quantity Produced", "Waste",
            "Downtime (mins)", "Status", "Section", "Machine", "Created By", "Created At"
        ])

        queryset = self.filter_queryset(self.get_queryset())
        for report in queryset:
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
        """Bulk import production reports from uploaded CSV with CREATE audit logging"""
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

                with transaction.atomic():
                    report = serializer.save(user=request.user)
                    ReportAuditTrail.objects.create(
                        report=report,
                        changed_by=request.user,
                        change_type=ReportAuditTrail.ChangeType.CREATE
                    )
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
            "Quantity Produced",
            "Waste",
            "Downtime (mins)",
            "Status",
            "Machine",
            "Remarks"
        ])
        return response

    @action(detail=False, methods=["post"])
    def preview_csv(self, request):
        """Preview CSV import without committing changes."""
        file_obj: InMemoryUploadedFile = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        decoded_file = file_obj.read().decode("utf-8")
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)

        preview_data = []
        errors = []

        for idx, row in enumerate(reader, start=1):
            try:
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
                preview_data.append(serializer.validated_data)
            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        preview_id = str(uuid.uuid4())
        cache.set(f"csv_preview_{preview_id}", preview_data, timeout=900)

        return Response(
            {"preview_id": preview_id, "preview": preview_data, "errors": errors},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"])
    def commit_csv(self, request):
        """Commit previously previewed CSV rows into the database."""
        preview_id = request.data.get("preview_id")
        if not preview_id:
            return Response({"error": "preview_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        preview_data = cache.get(f"csv_preview_{preview_id}")
        if not preview_data:
            return Response({"error": "Preview expired or not found"}, status=status.HTTP_400_BAD_REQUEST)

        created_reports = []
        try:
            with transaction.atomic():
                for data in preview_data:
                    report = ProductionReport.objects.create(user=request.user, **data)
                    created_reports.append(report)

                    ReportAuditTrail.objects.create(
                        report=report,
                        changed_by=request.user,
                        change_type=ReportAuditTrail.ChangeType.CREATE
                    )
            cache.delete(f"csv_preview_{preview_id}")
            return Response(
                {"created": ProductionReportSerializer(created_reports, many=True).data},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReportsRootView(APIView):
    """Custom root view for /api/reports/"""
    def get(self, request, format=None):
        links = {
            "production-reports": request.build_absolute_uri("/api/reports/production-reports/"),
        }
        reports = ProductionReport.objects.order_by("-created_at")[:10]
        serializer = ProductionReportSerializer(reports, many=True)
        return Response({"links": links, "latest_reports": serializer.data})
