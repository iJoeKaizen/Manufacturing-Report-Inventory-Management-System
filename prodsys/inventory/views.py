# inventory/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
import csv, io

from .models import Section, Machine
from .serializers import SectionSerializer, MachineSerializer


# --- Section CRUD ---
class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    # Export all sections as CSV
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sections.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name'])
        for section in self.queryset:
            writer.writerow([section.id, section.name])
        return response

    # Bulk import sections from CSV
    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        decoded = file.read().decode("utf-8")
        io_string = io.StringIO(decoded)
        reader = csv.DictReader(io_string)

        created = []
        errors = []
        for idx, row in enumerate(reader, start=1):
            serializer = self.get_serializer(data=row)
            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
                created.append(serializer.data)
            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return Response({"created": created, "errors": errors})


# --- Machine CRUD ---
class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.select_related('section').all()
    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'section__name']
    ordering_fields = ['name', 'section__name']
    ordering = ['name']

    # Filter machines by section
    @action(detail=False, methods=['get'])
    def by_section(self, request):
        section_id = request.query_params.get('section_id')
        machines = self.queryset.filter(section_id=section_id) if section_id else self.queryset.all()
        serializer = self.get_serializer(machines, many=True)
        return Response(serializer.data)

    # Export all machines as CSV
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="machines.csv"'
        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Section'])
        for machine in self.queryset:
            writer.writerow([machine.id, machine.name, machine.section.name if machine.section else ''])
        return response

    # Bulk import machines from CSV
    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        decoded = file.read().decode("utf-8")
        io_string = io.StringIO(decoded)
        reader = csv.DictReader(io_string)

        created = []
        errors = []
        for idx, row in enumerate(reader, start=1):
            # Ensure section exists
            section_name = row.get("section")
            section = None
            if section_name:
                from .models import Section
                section = Section.objects.filter(name=section_name).first()
                if not section:
                    errors.append({"row": idx, "error": f"Section '{section_name}' not found", "data": row})
                    continue
            row['section'] = section.id if section else None
            serializer = self.get_serializer(data=row)
            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
                created.append(serializer.data)
            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return Response({"created": created, "errors": errors})
