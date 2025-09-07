from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Section, Machine, MaterialConsumption
from .serializers import SectionSerializer, MachineSerializer, MaterialConsumptionSerializer

class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    queryset = Section.objects.all()

class MachineViewSet(viewsets.ModelViewSet):
    serializer_class = MachineSerializer
    queryset = Machine.objects.all()

class MaterialConsumptionViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialConsumptionSerializer
    queryset = MaterialConsumption.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaterialConsumption.objects.all()
        return qs.select_related("material", "report")
