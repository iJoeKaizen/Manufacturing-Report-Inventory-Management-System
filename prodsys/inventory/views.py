from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.timezone import now
from django.db.models import Sum, F
from rest_framework import viewsets, mixins, filters, status, decorators
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from datetime import timedelta

from .models import InventoryItem, StockMovement, MaterialRequest, deduct_stock
from .serializers import (
    InventoryItemSerializer,
    StockMovementSerializer,
    StockInSerializer,
    StockOutSerializer,
    StockAdjustSerializer,
    StockTransferSerializer,
    MaterialRequestSerializer,
)
from .filters import InventoryItemFilter, StockMovementFilter
from .permissions import InventoryPermission
from accounts.utils import get_user_role


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all().order_by("code")
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated, InventoryPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryItemFilter
    search_fields = ["code", "description", "name"]
    ordering_fields = ["code", "category", "quantity"]
    ordering = ["code"]

    def check_permission(self, action_name):
        role = get_user_role(self.request.user)
        perms = InventoryPermission.role_perms.get(role, {})
        allowed = perms.get(action_name, False)
        if allowed == False:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Role " + str(role) + " cannot do " + str(action_name))

    @action(detail=True, methods=["post"])
    def stock_in(self, request, pk=None):
        self.check_permission("stock_in")
        the_item = self.get_object()
        serializer = StockInSerializer(data=request.data)
        valid = serializer.is_valid()
        if not valid:
            serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        qty = data["quantity"]
        ref = data.get("reference", "")
        rem = data.get("remarks", "")
        old_qty = the_item.quantity
        new_qty = old_qty + qty
        the_item.quantity = new_qty
        the_item.save(update_fields=["quantity", "last_updated"])

        move = StockMovement()
        move.item = the_item
        move.movement_type = "IN"
        move.quantity = qty
        move.reference = ref
        move.remarks = rem
        move.created_by = request.user
        move.save()

        serialized = self.get_serializer(the_item)
        return Response(serialized.data)

    @action(detail=True, methods=["post"])
    def stock_out(self, request, pk=None):
        self.check_permission("stock_out")
        the_item = self.get_object()
        serializer = StockOutSerializer(data=request.data, context={"item": the_item})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        qty = data["quantity"]
        ref = data.get("reference", "")
        rem = data.get("remarks", "")
        old_qty = the_item.quantity
        if old_qty < qty:
            return Response({"detail": "Not enough stock"}, status=status.HTTP_400_BAD_REQUEST)
        new_qty = old_qty - qty
        the_item.quantity = new_qty
        the_item.save(update_fields=["quantity", "last_updated"])

        move = StockMovement()
        move.item = the_item
        move.movement_type = "OUT"
        move.quantity = qty
        move.reference = ref
        move.remarks = rem
        move.created_by = request.user
        move.save()

        serialized = self.get_serializer(the_item)
        return Response(serialized.data)

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        self.check_permission("adjust")
        the_item = self.get_object()
        serializer = StockAdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delta = serializer.validated_data["delta"]
        ref = serializer.validated_data.get("reference", "")
        rem = serializer.validated_data.get("remarks", "")
        old_qty = the_item.quantity
        new_qty = old_qty + delta
        if new_qty < 0:
            return Response({"detail": "Resulting quantity negative"}, status=status.HTTP_400_BAD_REQUEST)
        the_item.quantity = new_qty
        the_item.save(update_fields=["quantity", "last_updated"])

        move = StockMovement()
        move.item = the_item
        move.movement_type = "ADJUST"
        move.quantity = delta
        move.reference = ref
        move.remarks = rem
        move.created_by = request.user
        move.save()

        serialized = self.get_serializer(the_item)
        return Response(serialized.data)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        self.check_permission("transfer")
        from_item = self.get_object()
        serializer = StockTransferSerializer(data=request.data, context={"item": from_item})
        serializer.is_valid(raise_exception=True)
        to_item = serializer.validated_data["to_item"]
        qty = serializer.validated_data["quantity"]
        ref = serializer.validated_data.get("reference", "")
        rem = serializer.validated_data.get("remarks", "")
        old_from_qty = from_item.quantity
        old_to_qty = to_item.quantity
        if from_item.id == to_item.id:
            return Response({"detail": "Cannot transfer to same item"}, status=status.HTTP_400_BAD_REQUEST)
        if old_from_qty < qty:
            return Response({"detail": "Not enough stock to transfer"}, status=status.HTTP_400_BAD_REQUEST)
        new_from_qty = old_from_qty - qty
        from_item.quantity = new_from_qty
        from_item.save(update_fields=["quantity", "last_updated"])
        move_out = StockMovement()
        move_out.item = from_item
        move_out.movement_type = "TRANSFER"
        move_out.quantity = -qty
        move_out.reference = ref
        move_out.remarks = "To " + str(to_item.code)
        move_out.created_by = request.user
        move_out.save()

        new_to_qty = old_to_qty + qty
        to_item.quantity = new_to_qty
        to_item.save(update_fields=["quantity", "last_updated"])
        move_in = StockMovement()
        move_in.item = to_item
        move_in.movement_type = "TRANSFER"
        move_in.quantity = qty
        move_in.reference = ref
        move_in.remarks = "From " + str(from_item.code)
        move_in.created_by = request.user
        move_in.save()

        return Response({"from": InventoryItemSerializer(from_item).data, "to": InventoryItemSerializer(to_item).data})


class MaterialRequestViewSet(viewsets.ModelViewSet):
    queryset = MaterialRequest.objects.select_related("requested_by", "stock_item").all()
    serializer_class = MaterialRequestSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        status_now = req.status
        if status_now != "PENDING":
            return Response({"detail": "Already processed"}, status=status.HTTP_400_BAD_REQUEST)
        item = req.stock_item
        qty = req.po_quantity
        old_qty = item.quantity
        if old_qty < qty:
            return Response({"detail": "Not enough stock for " + str(item.code)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            deduct_stock({item.id: qty}, reference="Req " + str(req.id), user=request.user)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        req.status = "APPROVED"
        req.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        status_now = req.status
        if status_now != "PENDING":
            return Response({"detail": "Already processed"}, status=status.HTTP_400_BAD_REQUEST)
        req.status = "REJECTED"
        req.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(req).data)


class StockMovementViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = StockMovement.objects.select_related("item").order_by("-timestamp")
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    filterset_class = StockMovementFilter
    ordering_fields = ["timestamp", "quantity", "movement_type"]
    ordering = ["-timestamp"]

    @decorators.action(detail=True, methods=["get"])
    def trace(self, request, pk=None):
        move = self.get_object()
        item = move.item
        history = StockMovement.objects.filter(item=item).order_by("timestamp")
        serialized_move = StockMovementSerializer(move).data
        serialized_history = StockMovementSerializer(history, many=True).data
        return Response({"movement": serialized_move, "item": item.name, "history": serialized_history})


class InventoryDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        totals = InventoryItem.objects.values("category").annotate(total_qty=Sum("quantity")).order_by("category")
        totals_by_cat = {}
        for t in totals:
            cat = t["category"]
            qty = t["total_qty"]
            if qty is None:
                qty = 0
            totals_by_cat[cat] = str(qty)

        low_items = InventoryItem.objects.filter(quantity__lte=F("reorder_level"))
        low_items_data = InventoryItemSerializer(low_items[:50], many=True).data

        recent_moves = StockMovement.objects.select_related("item").order_by("-timestamp")[:10]
        recent_serialized = StockMovementSerializer(recent_moves, many=True).data

        def sum_moves(since):
            q = StockMovement.objects.filter(timestamp__date__gte=since).values("movement_type").annotate(total=Sum("quantity"))
            return list(q)

        return Response({
            "totals_by_category": totals_by_cat,
            "low_stock_count": low_items.count(),
            "low_stock_items": low_items_data,
            "recent_movements": recent_serialized,
            "daily_movements": sum_moves(today),
            "weekly_movements": sum_moves(week_start),
            "monthly_movements": sum_moves(month_start),
            "yearly_movements": sum_moves(year_start),
            "role": get_user_role(request.user),
        })


class InventoryDashboardPage(LoginRequiredMixin, TemplateView):
    template_name = "inventory/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = now().date()
        start_week = today - timedelta(days=today.weekday())
        start_month = today.replace(day=1)
        start_year = today.replace(month=1, day=1)

        def count_moves(since):
            return StockMovement.objects.filter(timestamp__date__gte=since).count()

        totals = InventoryItem.objects.values("category").annotate(total_qty=Sum("quantity")).order_by("category")
        context["totals_by_category"] = totals

        low_items = InventoryItem.objects.filter(quantity__lte=F("reorder_level"))
        context["low_stock_count"] = low_items.count()
        context["low_stock_items"] = low_items[:50]

        recent = StockMovement.objects.select_related("item").order_by("-timestamp")[:10]
        context["recent_movements"] = recent

        context["daily_movements"] = count_moves(today)
        context["weekly_movements"] = count_moves(start_week)
        context["monthly_movements"] = count_moves(start_month)
        context["yearly_movements"] = count_moves(start_year)

        role = get_user_role(self.request.user)
        context["role"] = role

        menu_base = {
            "OPERATOR": [{"name": "Inventory", "url": "/inventory/"}, {"name": "Production", "url": "/api/production/"}],
            "SUPERVISOR": [{"name": "Inventory", "url": "/inventory/"}, {"name": "Production", "url": "/api/production/"},
                           {"name": "Reports", "url": "/api/reports/"}],
            "MANAGER": [{"name": "Inventory", "url": "/inventory/"}, {"name": "Production", "url": "/api/production/"},
                        {"name": "Reports", "url": "/api/reports/"}, {"name": "Accounts", "url": "/api/auth/users/"}],
            "ADMIN": [{"name": "Inventory", "url": "/inventory/"}, {"name": "Production", "url": "/api/production/"},
                      {"name": "Reports", "url": "/api/reports/"}, {"name": "Accounts", "url": "/api/auth/users/"},
                      {"name": "Admin Settings", "url": "/admin/"}],
        }

        context["menu"] = menu_base.get(role, menu_base["OPERATOR"])
        context["show_analytics"] = role in ["SUPERVISOR", "MANAGER", "ADMIN"]

        return context
