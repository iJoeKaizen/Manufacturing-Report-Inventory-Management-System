# reports/urls.py
from rest_framework.routers import DefaultRouter
from .views import ProductionReportViewSet

router = DefaultRouter()
router.register(r'production-reports', ProductionReportViewSet, basename='production-report')

urlpatterns = router.urls
