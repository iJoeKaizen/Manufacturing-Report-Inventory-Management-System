from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InventoryItemViewSet,
    StockMovementViewSet,
    InventoryDashboardView,
    InventoryPageView
)

router = DefaultRouter()
router.register(r"items", InventoryItemViewSet, basename="inventory-items")
router.register(r"movements", StockMovementViewSet, basename="inventory-movements")

urlpatterns = [
    path("dashboard/", InventoryDashboardView.as_view(), name="inventory-dashboard"),
    path("api/", include(router.urls)),   # <-- JSON API endpoints
    path("", InventoryPageView.as_view(), name="inventory"),  # <-- Web dashboard
]
