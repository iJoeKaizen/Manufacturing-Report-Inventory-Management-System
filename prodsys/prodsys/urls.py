from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from production.views import SectionViewSet, MachineViewSet
from core.views import DashboardView, UserViewSet  # add user role assignment viewset

router = DefaultRouter()
router.register(r'sections', SectionViewSet)
router.register(r'machines', MachineViewSet)
router.register(r'users', UserViewSet, basename="users")  # only Admin can assign roles

urlpatterns = [
    path("admin/", admin.site.urls),

    # Browsable API login/logout (optional for DRF UI)
    path("api/auth/", include("rest_framework.urls")),

    # Root → redirect to dashboard
    path("", lambda request: redirect("dashboard/")),

    # Dashboard (requires login)
    path("dashboard/", login_required(DashboardView.as_view()), name="dashboard"),

    # JWT Authentication
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # Local apps
    path("api/core/", include("core.urls")),       # core app (register, roles, etc.)
    path("inventory/", include("inventory.urls")),  
    path("api/reports/", include("reports.urls")), 
    path("api/summary/", include("summary.urls")), 
    path("api/production/", include(router.urls)),
]
