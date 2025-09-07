from django.urls import path, include
from django.contrib.auth.decorators import login_required
from rest_framework.routers import DefaultRouter
from .views import (
    InventoryItemViewSet,
    StockMovementViewSet,
    MaterialRequestViewSet,
    InventoryDashboardAPIView,   # JSON API view
    InventoryDashboardPage,      # HTML dashboard
)

app_name = "inventory"
# DRF router
router = DefaultRouter()
router.register(r"items", InventoryItemViewSet, basename="inventoryitem")
router.register(r"movements", StockMovementViewSet, basename="inventorymovements")
router.register(r"material-requests", MaterialRequestViewSet, basename="material-requests")

# URL patterns
urlpatterns = [
    path("dashboard/api/", login_required(InventoryDashboardAPIView.as_view()), name="inventory-dashboard-api"),  # JSON
    path("dashboard/", login_required(InventoryDashboardPage.as_view()), name="inventory-dashboard-page"),  # HTML
    path("", include(router.urls)),
]
