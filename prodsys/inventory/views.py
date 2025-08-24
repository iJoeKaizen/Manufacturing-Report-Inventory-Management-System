from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
import csv

from .models import Section, Machine, ProductionReport
from .serializers import SectionSerializer, MachineSerializer
from reports.serializers import ProductionReportSerializer

# --- Section CRUD ---
class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

# --- Machine CRUD ---
class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.select_related('section').all()
    serializer_class = MachineSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'section__name']
    ordering_fields = ['name', 'section__name']
    ordering = ['name']

    def by_section(self, request):
        """Return machines filtered by section_id"""
        section_id = request.query_params.get('section_id')
        if section_id:
            machines = self.queryset.filter(section_id=section_id)
        else:
            machines = self.queryset.all()
        serializer = self.get_serializer(machines, many=True)
        return Response(serializer.data)

# --- ProductionReport CRUD ---
class ProductionReportViewSet(viewsets.ModelViewSet):
    queryset = ProductionReport.objects.select_related('section', 'machine', 'created_by').all()
    serializer_class = ProductionReportSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['job_id', 'product_name', 'status', 'section__name', 'machine__name']
    ordering_fields = ['date', 'quantity', 'status', 'created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
    # If machine is provided but section is missing, auto-fill it
        machine = serializer.validated_data.get('machine')
        if machine and not serializer.validated_data.get('section'):
            serializer.save(created_by=self.request.user, section=machine.section)
        else:
            serializer.save(created_by=self.request.user)


    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a production report"""
        report = self.get_object()
        report.approved = True
        report.save()
        return Response({'status': 'approved'})

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export all production reports as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="production_reports.csv"'

        writer = csv.writer(response)
        writer.writerow(['Job ID', 'Product Name', 'Quantity', 'Date', 'Status', 'Approved', 'Section', 'Machine', 'Created By', 'Created At'])

        for report in self.queryset:
            writer.writerow([
                report.job_id,
                report.product_name,
                report.quantity,
                report.date,
                report.status,
                report.approved,
                report.section.name if report.section else '',
                report.machine.name if report.machine else '',
                report.created_by.username if report.created_by else '',
                report.created_at,
            ])

        return response
