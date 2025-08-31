# inventory/views.py
from django.views.generic import TemplateView
from rest_framework import viewsets, mixins, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.http import StreamingHttpResponse, HttpResponseBadRequest
from django.db import transaction, models
from django_filters.rest_framework import DjangoFilterBackend
from decimal import Decimal

from .models import InventoryItem, StockMovement, InventoryCategory, deduct_stock
from .serializers import (
    InventoryItemSerializer,
    StockMovementSerializer,
    StockInSerializer,
    StockOutSerializer,
    StockAdjustSerializer,
    StockTransferSerializer,
)
from .filters import InventoryItemFilter, StockMovementFilter


# --- Inventory CRUD ---
class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().order_by("code")
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryItemFilter
    search_fields = ["code", "description", "name"]
    ordering_fields = ["code", "category", "quantity"]
    ordering = ["code"]

    # ------------------- Stock Actions -------------------
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def stock_in(self, request, pk=None):
        item = self.get_object()
        serializer = StockInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        item.quantity += data["quantity"]
        item.save(update_fields=["quantity", "last_updated"])

        StockMovement.objects.create(
            item=item,
            movement_type="IN",
            quantity=data["quantity"],
            reference=data.get("reference"),
            remarks=data.get("remarks"),
            created_by=request.user
        )
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def stock_out(self, request, pk=None):
        item = self.get_object()
        serializer = StockOutSerializer(data=request.data, context={"item": item})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if item.quantity < data["quantity"]:
            return Response({"detail": "Insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)

        item.quantity -= data["quantity"]
        item.save(update_fields=["quantity", "last_updated"])

        StockMovement.objects.create(
            item=item,
            movement_type="OUT",
            quantity=data["quantity"],
            reference=data.get("reference"),
            remarks=data.get("remarks"),
            created_by=request.user
        )
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def adjust(self, request, pk=None):
        item = self.get_object()
        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delta = serializer.validated_data["delta"]

        new_qty = item.quantity + delta
        if new_qty < 0:
            return Response({"detail": "Resulting quantity would be negative."},
                            status=status.HTTP_400_BAD_REQUEST)

        item.quantity = new_qty
        item.save(update_fields=["quantity", "last_updated"])

        StockMovement.objects.create(
            item=item,
            movement_type="ADJUST",
            quantity=delta,  # signed delta
            reference=serializer.validated_data.get("reference"),
            remarks=serializer.validated_data.get("remarks"),
            created_by=request.user
        )
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def transfer(self, request, pk=None):
        from_item = self.get_object()
        serializer = StockTransferSerializer(data=request.data, context={"item": from_item})
        serializer.is_valid(raise_exception=True)
        to_item = serializer.validated_data["to_item"]
        qty = serializer.validated_data["quantity"]

        if from_item.id == to_item.id:
            return Response({"detail": "Cannot transfer to the same item."}, status=status.HTTP_400_BAD_REQUEST)
        if from_item.quantity < qty:
            return Response({"detail": "Insufficient stock."}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct from source
        from_item.quantity -= qty
        from_item.save(update_fields=["quantity", "last_updated"])
        StockMovement.objects.create(
            item=from_item,
            movement_type="TRANSFER",
            quantity=-qty,
            reference=serializer.validated_data.get("reference"),
            remarks=f"Transfer to {to_item.code}. " + (serializer.validated_data.get("remarks") or ""),
            created_by=request.user
        )

        # Add to destination
        to_item.quantity += qty
        to_item.save(update_fields=["quantity", "last_updated"])
        StockMovement.objects.create(
            item=to_item,
            movement_type="TRANSFER",
            quantity=qty,
            reference=serializer.validated_data.get("reference"),
            remarks=f"Transfer from {from_item.code}. " + (serializer.validated_data.get("remarks") or ""),
            created_by=request.user
        )

        return Response({
            "from": InventoryItemSerializer(from_item).data,
            "to": InventoryItemSerializer(to_item).data,
        })

    # ------------------- Export CSV -------------------
    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())

        def row_iter():
            header = [
                "code","name","category","description","uom",
                "quantity","reorder_level","last_updated",
            ]
            yield ",".join(header) + "\n"
            for i in qs.iterator():
                row = [
                    i.code,
                    i.name,
                    i.category,
                    (i.description or "").replace(",", " "),
                    i.uom,
                    str(i.quantity),
                    str(i.reorder_level),
                    i.last_updated.isoformat(),
                ]
                yield ",".join(row) + "\n"

        resp = StreamingHttpResponse(row_iter(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="inventory_export.csv"'
        return resp

    # ------------------- Export PDF -------------------
    @action(detail=False, methods=["get"])
    def export_pdf(self, request):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from io import BytesIO
        except ImportError:
            return HttpResponseBadRequest("PDF export requires reportlab. Install with: pip install reportlab")

        qs = self.filter_queryset(self.get_queryset())
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        y = height - 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, y, "Inventory Export")
        y -= 20
        c.setFont("Helvetica", 9)

        for i in qs.iterator():
            line = f"{i.code} | {i.name} | {i.category} | {i.uom} | Qty: {i.quantity} | Reorder: {i.reorder_level}"
            if y < 60:
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 9)
            c.drawString(40, y, line[:120])
            y -= 12

        c.showPage()
        c.save()
        buf.seek(0)

        resp = StreamingHttpResponse(buf, content_type="application/pdf")
        resp["Content-Disposition"] = 'attachment; filename="inventory_export.pdf"'
        return resp


# --- Stock Movements ViewSet ---
class StockMovementViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    queryset = StockMovement.objects.select_related("item").order_by("-timestamp")
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = StockMovementFilter
    ordering_fields = ["timestamp", "quantity", "movement_type"]
    ordering = ["-timestamp"]


# --- Dashboard API ---
class InventoryDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        totals = (InventoryItem.objects
                  .values("category")
                  .annotate(total_qty=models.Sum("quantity"))
                  .order_by("category"))
        totals_by_category = {t["category"]: str(t["total_qty"] or 0) for t in totals}

        low = InventoryItem.objects.filter(quantity__lte=models.F("reorder_level"))
        low_count = low.count()
        low_items = InventoryItemSerializer(low[:50], many=True).data

        recent = StockMovement.objects.select_related("item").order_by("-timestamp")[:10]
        recent_serialized = StockMovementSerializer(recent, many=True).data

        # --- Role-based permissions for frontend ---
        role = getattr(request.user, "role", "OPERATOR").upper()
        permissions_map = {
            "OPERATOR": {"can_edit": False, "can_delete": False, "can_stock_in_out": True},
            "SUPERVISOR": {"can_edit": False, "can_delete": False, "can_stock_in_out": True},
            "MANAGER": {"can_edit": True, "can_delete": True, "can_stock_in_out": True},
            "ADMIN": {"can_edit": True, "can_delete": True, "can_stock_in_out": True},
        }
        role_permissions = permissions_map.get(role, {"can_edit": False, "can_delete": False, "can_stock_in_out": False})

        return Response({
            "totals_by_category": totals_by_category,
            "low_stock_count": low_count,
            "low_stock_items": low_items,
            "recent_movements": recent_serialized,
            "permissions": role_permissions,
            "role": role,
        })


# --- Inventory Template Page ---
class InventoryPageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "inventory.html"

    def test_func(self):
        return getattr(self.request.user, "role", "").upper() in ["OPERATOR", "MANAGER", "ADMIN"]

    def handle_no_permission(self):
        return redirect("dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = getattr(self.request.user, "role", "OPERATOR").upper()
        context["role"] = role

        # Base API endpoints
        context["inventory_api_url"] = "/api/inventory/items/"
        context["dashboard_api_url"] = "/api/inventory/dashboard/"

        # Role-based permissions for frontend buttons
        permissions_map = {
            "OPERATOR": {"can_edit": False, "can_delete": False, "can_stock_in_out": True},
            "SUPERVISOR": {"can_edit": False, "can_delete": False, "can_stock_in_out": True},
            "MANAGER": {"can_edit": True, "can_delete": True, "can_stock_in_out": True},
            "ADMIN": {"can_edit": True, "can_delete": True, "can_stock_in_out": True},
        }
        context["permissions"] = permissions_map.get(role, {"can_edit": False, "can_delete": False, "can_stock_in_out": False})
        return context