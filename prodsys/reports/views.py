import csv
import io
import uuid
from django.utils.timezone import now
from django.db import transaction
from django.core.cache import cache
from django.http import HttpResponse
from django.core.files.uploadedfile import InMemoryUploadedFile

from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError

from accounts.permissions import ReportPermission
from .models import ProductionReport, ReportAuditTrail
from .serializers import ProductionReportSerializer, ReportAuditTrailSerializer
from .filters import ProductionReportFilter

from production.models import Machine, MaterialConsumption
from production.serializers import MaterialConsumptionSerializer

try:
    from inventory.models import StockMovement
    from .serializers import StockMovementSerializer
except Exception:
    StockMovement = None
    StockMovementSerializer = None

class IsAdminOrReportPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True
        return ReportPermission().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True
        return ReportPermission().has_object_permission(request, view, obj)

class ProductionReportViewSet(viewsets.ModelViewSet):
    queryset = ProductionReport.objects.select_related("machine", "section", "user").all()
    serializer_class = ProductionReportSerializer
    permission_classes = [IsAdminOrReportPermission]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductionReportFilter
    search_fields = ["job_number"]
    ordering_fields = ["created_at", "quantity_produced", "status"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        machine = serializer.validated_data.get("machine")
        section = serializer.validated_data.get("section")
        if machine and not section:
            report = serializer.save(user=self.request.user, section=machine.section)
        else:
            report = serializer.save(user=self.request.user)
        ReportAuditTrail.objects.create(report=report, changed_by=self.request.user,
                                        change_type=ReportAuditTrail.ChangeType.CREATE)

    def perform_update(self, serializer):
        report = self.get_object()
        if report.status == ProductionReport.Status.APPROVED:
            raise ValidationError("Cannot modify approved report")
        machine = serializer.validated_data.get("machine")
        section = serializer.validated_data.get("section")
        if machine and not section:
            report = serializer.save(section=machine.section)
        else:
            report = serializer.save()
        ReportAuditTrail.objects.create(report=report, changed_by=self.request.user,
                                        change_type=ReportAuditTrail.ChangeType.UPDATE)

    def destroy(self, request, *args, **kwargs):
        report = self.get_object()
        if report.status == ProductionReport.Status.APPROVED:
            return Response({"error": "Cannot delete approved report"}, status=status.HTTP_400_BAD_REQUEST)
        report._deleted_by = request.user
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        report = self.get_object()
        if report.status == ProductionReport.Status.APPROVED:
            return Response({"detail": "Report already approved"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            report.status = ProductionReport.Status.APPROVED
            report.approved_at = now()
            report.save()
            ReportAuditTrail.objects.create(report=report, changed_by=request.user,
                                            change_type=ReportAuditTrail.ChangeType.APPROVE)
        return Response({"status": "approved"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="production_reports.csv"'
        writer = csv.writer(response)
        writer.writerow(["Job Number","Product Name","Quantity Produced","Waste","Downtime","Status","Section","Machine","Created By","Created At"])
        for report in self.filter_queryset(self.get_queryset()):
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
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        decoded_file = file_obj.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded_file))
        created_reports, errors = [], []
        for idx, row in enumerate(reader, start=1):
            try:
                machine_name = row.get("Machine")
                if not machine_name:
                    raise ValueError("Machine required")
                machine = Machine.objects.get(name=machine_name)
                section = machine.section
                data = {
                    "job_number": row.get("Job Number"),
                    "quantity_produced": int(row.get("Quantity Produced") or 0),
                    "waste": float(row.get("Waste") or 0),
                    "downtime_minutes": int(row.get("Downtime") or 0),
                    "status": row.get("Status","DRAFT").upper(),
                    "machine": machine.id,
                    "section": section.id if section else None,
                    "remarks": row.get("Remarks",""),
                }
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                with transaction.atomic():
                    report = serializer.save(user=request.user)
                    ReportAuditTrail.objects.create(report=report, changed_by=request.user,
                                                    change_type=ReportAuditTrail.ChangeType.CREATE)
                created_reports.append(serializer.data)
            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})
        return Response({"created": created_reports, "errors": errors},
                        status=status.HTTP_201_CREATED if created_reports else status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def download_csv_template(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="production_report_template.csv"'
        writer = csv.writer(response)
        writer.writerow(["Job Number","Quantity Produced","Waste","Downtime","Status","Machine","Remarks"])
        return response

    @action(detail=False, methods=["post"])
    def preview_csv(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        decoded_file = file_obj.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded_file))
        preview_data, errors = [], []
        for idx, row in enumerate(reader, start=1):
            try:
                machine_name = row.get("Machine")
                if not machine_name:
                    raise ValueError("Machine required")
                machine = Machine.objects.get(name=machine_name)
                section = machine.section
                data = {
                    "job_number": row.get("Job Number"),
                    "quantity_produced": int(row.get("Quantity Produced") or 0),
                    "waste": float(row.get("Waste") or 0),
                    "downtime_minutes": int(row.get("Downtime") or 0),
                    "status": row.get("Status","DRAFT").upper(),
                    "machine": machine.id,
                    "section": section.id if section else None,
                    "remarks": row.get("Remarks",""),
                }
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                preview_data.append(serializer.validated_data)
            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})
        preview_id = str(uuid.uuid4())
        cache.set(f"csv_preview_{preview_id}", preview_data, timeout=900)
        return Response({"preview_id": preview_id, "preview": preview_data, "errors": errors})

    @action(detail=False, methods=["post"])
    def commit_csv(self, request):
        preview_id = request.data.get("preview_id")
        if not preview_id:
            return Response({"error": "preview_id required"}, status=status.HTTP_400_BAD_REQUEST)
        preview_data = cache.get(f"csv_preview_{preview_id}")
        if not preview_data:
            return Response({"error": "Preview expired or missing"}, status=status.HTTP_400_BAD_REQUEST)
        created_reports = []
        with transaction.atomic():
            for data in preview_data:
                report = ProductionReport.objects.create(user=request.user, **data)
                created_reports.append(report)
                ReportAuditTrail.objects.create(report=report, changed_by=request.user,
                                                change_type=ReportAuditTrail.ChangeType.CREATE)
        cache.delete(f"csv_preview_{preview_id}")
        return Response({"created": ProductionReportSerializer(created_reports, many=True).data},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="usage")
    def usage(self, request, pk=None):
        report = self.get_object()
        consumptions = MaterialConsumption.objects.filter(report=report)
        cons_data = MaterialConsumptionSerializer(consumptions, many=True).data
        moves_data = []
        if StockMovement and StockMovementSerializer:
            moves = StockMovement.objects.filter(reference__icontains=f"Report {report.id}")
            moves_data = StockMovementSerializer(moves, many=True).data
        return Response({
            "report_id": report.id,
            "job_number": getattr(report, "job_number", None),
            "status": report.status,
            "consumptions": cons_data,
            "stock_movements": moves_data,
        })

    @action(detail=True, methods=["get"], url_path="audit-trail")
    def audit_trail(self, request, pk=None):
        report = self.get_object()
        logs = report.audit_trails.all().order_by("-timestamp")
        serializer = ReportAuditTrailSerializer(logs, many=True)
        return Response(serializer.data)

class ReportsRootView(APIView):
    def get(self, request, format=None):
        links = {"production-reports": request.build_absolute_uri("/api/reports/production-reports/")}
        reports = ProductionReport.objects.order_by("-created_at")[:10]
        serializer = ProductionReportSerializer(reports, many=True)
        return Response({"links": links, "latest_reports": serializer.data})

class AuditTrailViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReportAuditTrail.objects.all().order_by("-timestamp")
    serializer_class = ReportAuditTrailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(changed_by=user)
