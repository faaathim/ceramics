# reports/services.py

from datetime import date, timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from orders.models import Order


class SalesReportService:
    """
    Handles all sales report filtering and aggregation logic.
    """

    def __init__(self, report_type=None, start_date=None, end_date=None):
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        self._set_date_range()

    # -----------------------------
    # SET DATE RANGE
    # -----------------------------
    def _set_date_range(self):
        today = date.today()

        if self.report_type == "daily":
            self.start_date = today
            self.end_date = today

        elif self.report_type == "weekly":
            self.start_date = today - timedelta(days=7)
            self.end_date = today

        elif self.report_type == "monthly":
            self.start_date = today.replace(day=1)
            self.end_date = today

        elif self.report_type == "yearly":
            self.start_date = today.replace(month=1, day=1)
            self.end_date = today

    # -----------------------------
    # BASE QUERYSET
    # -----------------------------
    def get_queryset(self):
        queryset = Order.objects.filter(status="DELIVERED")

        if self.start_date and self.end_date:
            queryset = queryset.filter(
                created_at__date__range=[self.start_date, self.end_date]
            )

        return queryset

    # -----------------------------
    # SUMMARY DATA
    # -----------------------------
    def get_summary(self):
        queryset = self.get_queryset()

        summary = queryset.aggregate(
            total_orders=Count("id"),
            total_subtotal=Sum("subtotal"),
            total_discount=Sum("discount_amount"),
            total_tax=Sum("tax_amount"),
            total_shipping=Sum("shipping_charge"),
            total_revenue=Sum("total_amount"),
        )

        # Replace None with 0
        for key in summary:
            summary[key] = summary[key] or 0

        return summary

    # -----------------------------
    # CHART DATA
    # -----------------------------
    def get_chart_data(self):
        queryset = self.get_queryset()

        if self.report_type in ["daily", "weekly"]:
            queryset = queryset.annotate(period=TruncDay("created_at"))

        elif self.report_type == "monthly":
            queryset = queryset.annotate(period=TruncMonth("created_at"))

        elif self.report_type == "yearly":
            queryset = queryset.annotate(period=TruncYear("created_at"))

        else:
            queryset = queryset.annotate(period=TruncDay("created_at"))

        return (
            queryset.values("period")
            .annotate(total=Sum("total_amount"))
            .order_by("period")
        )
