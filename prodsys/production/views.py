# production/views.py
from rest_framework import viewsets
from .models import Section, Machine
from .serializers import SectionSerializer, MachineSerializer


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer


class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer
