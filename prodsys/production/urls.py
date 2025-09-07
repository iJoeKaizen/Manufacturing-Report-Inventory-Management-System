from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MachineViewSet, SectionViewSet, MaterialConsumptionViewSet

router = DefaultRouter()
router.register("machines", MachineViewSet, basename="machine")
router.register("sections", SectionViewSet, basename="section")
router.register("consumptions", MaterialConsumptionViewSet, basename="consumption")

urlpatterns = [
    path("", include(router.urls)),
]
