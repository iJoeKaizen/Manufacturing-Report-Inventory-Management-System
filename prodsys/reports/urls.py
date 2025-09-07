# reports/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductionReportViewSet, ReportsRootView, AuditTrailViewSet

app_name = "reports"

router = DefaultRouter()
router.register(r'production-reports', ProductionReportViewSet, basename='production-report')
router.register(r"audit-trail", AuditTrailViewSet, basename="audit-trail") 


urlpatterns = [
    path('', ReportsRootView.as_view(), name='reports-root'),  # root view
    path('', include(router.urls)),  # viewset endpoints
]

