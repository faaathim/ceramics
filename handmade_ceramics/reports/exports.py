# reports/exports.py

import openpyxl
from django.http import HttpResponse
from django.utils.timezone import now


# ===============================
# EXCEL EXPORT
# ===============================
def export_sales_excel(orders, summary):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sales Report"

    headers = [
        "Order ID",
        "User",
        "Date",
        "Subtotal",
        "Discount",
        "Total Amount",
    ]

    sheet.append(headers)

    for order in orders:
        sheet.append([
            order.order_id,
            str(order.user),
            order.created_at.strftime("%Y-%m-%d"),
            float(order.subtotal),
            float(order.discount_amount),
            float(order.total_amount),
        ])

    sheet.append([])
    sheet.append(["Total Orders", summary["total_orders"]])
    sheet.append(["Total Subtotal", float(summary["total_subtotal"])])
    sheet.append(["Total Discount", float(summary["total_discount"])])
    sheet.append(["Total Revenue", float(summary["total_revenue"])])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="sales_report_{now().date()}.xlsx"'

    workbook.save(response)
    return response


# ===============================
# PDF EXPORT (ReportLab)
# ===============================
def export_sales_pdf(request, orders, summary):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    elements.append(Paragraph("<b>Sales Report</b>", styles['Title']))
    elements.append(Spacer(1, 0.4 * inch))

    # Summary Table
    summary_data = [
        ["Total Orders", summary["total_orders"]],
        ["Total Subtotal", f"₹ {summary['total_subtotal']}"],
        ["Total Discount", f"₹ {summary['total_discount']}"],
        ["Total Revenue", f"₹ {summary['total_revenue']}"],
    ]

    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * inch))

    # Orders Table
    table_data = [
        ["Order ID", "User", "Date", "Subtotal", "Discount", "Total"]
    ]

    for order in orders:
        table_data.append([
            order.order_id,
            str(order.user),
            order.created_at.strftime("%Y-%m-%d"),
            f"₹ {order.subtotal}",
            f"₹ {order.discount_amount}",
            f"₹ {order.total_amount}",
        ])

    orders_table = Table(table_data, repeatRows=1)
    orders_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))

    elements.append(orders_table)

    doc.build(elements)
    return response
