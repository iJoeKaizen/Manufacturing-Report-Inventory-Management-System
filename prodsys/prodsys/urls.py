from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter

from production.views import SectionViewSet, MachineViewSet
from core.views import DashboardView, UserViewSet

router = DefaultRouter()
router.register(r"sections", SectionViewSet)
router.register(r"machines", MachineViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Browsable API login/logout (only for DRF UI)
    path("api/auth/browsable/", include("rest_framework.urls")),

    # Root → redirect to dashboard
    path("", lambda request: redirect("dashboard/")),

    # Dashboard (requires login)
    path("dashboard/", login_required(DashboardView.as_view()), name="dashboard"),

    # Auth (centralized in accounts.urls)
    path("api/auth/", include("accounts.urls")),

        # Web login/logout (Django's built-in)
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/login/"), name="logout"),

    # Local apps
    path("api/core/", include("core.urls")),
    path("api/inventory/", include("inventory.urls")),
    # path("inventory/", include("inventory.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/summary/", include("summary.urls")),
    path("api/production/", include(router.urls)),
    path("api/production/", include("production.urls")), 
]
