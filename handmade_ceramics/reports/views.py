from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from .services import SalesReportService
from .exports import export_sales_excel, export_sales_pdf


def superuser_required(view_func):
    return user_passes_test(
        lambda u: u.is_superuser,
        login_url="admin:login"
    )(view_func)


@superuser_required
def sales_report_view(request):

    report_type = request.GET.get("report_type")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    export_type = request.GET.get("export")

    service = SalesReportService(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date
    )

    summary = service.get_summary()
    chart_data = service.get_chart_data()
    orders_queryset = service.get_queryset()

    # EXPORT
    if export_type == "excel":
        return export_sales_excel(orders_queryset, summary)

    if export_type == "pdf":
        return export_sales_pdf(request, orders_queryset, summary)

    # PAGINATION
    paginator = Paginator(orders_queryset, 10)
    page_number = request.GET.get("page")
    orders = paginator.get_page(page_number)

    context = {
        "summary": summary,
        "orders": orders,
        "chart_data": chart_data,
        "report_type": report_type,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "reports/sales_report.html", context)
