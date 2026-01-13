# orders/admin_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from .models import Order, OrderItem
from product_management.models import Variant
from django.db import transaction

# Simple superuser check reused in your custom_admin
def superuser_check(user):
    return user.is_active and user.is_superuser

# ---------------------------
# Admin: Order list view
# ---------------------------
@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_order_list(request):
    """
    Admin order list with search, filters, sort and pagination.

    Query params:
      - q: text search (order_id, user email, user first/last name)
      - status: order status filter
      - date_from, date_to: YYYY-MM-DD
      - sort: created_at / -created_at / total_amount / -total_amount
      - page: page number
    """
    qs = Order.objects.select_related('user').all()  # base queryset

    # 1) Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(order_id__icontains=q) |
            Q(user__email__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q)
        )

    # 2) Status filter
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)

    # 3) Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        try:
            dt_from = timezone.datetime.fromisoformat(date_from)
            qs = qs.filter(created_at__date__gte=dt_from.date())
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = timezone.datetime.fromisoformat(date_to)
            qs = qs.filter(created_at__date__lte=dt_to.date())
        except ValueError:
            pass

    # 4) Sorting
    sort = request.GET.get('sort', '-created_at')
    allowed_sorts = ['created_at', '-created_at', 'total_amount', '-total_amount']
    if sort not in allowed_sorts:
        sort = '-created_at'
    qs = qs.order_by(sort)

    # 5) Pagination
    page = request.GET.get('page', 1)
    per_page = 10
    paginator = Paginator(qs, per_page)
    try:
        orders_page = paginator.page(page)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    # Preserve querystring params for pagination links
    query_params = request.GET.copy()
    if 'page' in query_params:
        query_params.pop('page')

    context = {
        'orders': orders_page,
        'paginator': paginator,
        'query_params': query_params.urlencode(),
        'q': q,
        'status': status,
        'status_choices': Order._meta.get_field('status').choices,
        'date_from': date_from,
        'date_to': date_to,
        'sort': sort,
    }
    return render(request, 'orders/admin_order_list.html', context)


# ---------------------------
# Admin: Order detail view
# ---------------------------
@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_order_detail(request, order_id):
    """
    Show one order detail and allow changing overall order status.
    Status updates are done via POST to the same URL (PRG pattern).
    """
    order = get_object_or_404(Order, order_id=order_id)
    items = order.items.select_related('variant', 'product').all()

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if not order.can_change_status(new_status):
            messages.error(
                request,
                f"Invalid status change from "
                f"{order.get_status_display()} to "
                f"{new_status.replace('_', ' ').title()}."
            )
            return redirect(reverse(
                'custom_admin:orders_admin:admin_order_detail',
                args=[order.order_id]
            ))

        order.status = new_status
        order.save()
        messages.success(
            request,
            f"Order status updated to {order.get_status_display()}."
        )
        return redirect(reverse(
            'custom_admin:orders_admin:admin_order_detail',
            args=[order.order_id]
        ))

    context = {
        'order': order,
        'items': items,
        'status_choices': Order._meta.get_field('status').choices,
    }
    return render(request, 'orders/admin_order_detail.html', context)



# ---------------------------
# Admin: Inventory view (read & quick update link)
# ---------------------------
@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_inventory(request):
    """
    Basic inventory table showing variants and stock.
    This page currently lists items and provides an 'Edit' link to product admin.
    """
    variants = Variant.objects.select_related('product').order_by('-updated_at')
    # pagination for inventory (optional)
    page = request.GET.get('page', 1)
    paginator = Paginator(variants, 25)
    try:
        variants_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        variants_page = paginator.page(1)

    context = {
        'variants': variants_page,
        'query_params': '',
    }
    return render(request, 'orders/admin_inventory.html', context)
    
@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
def admin_verify_return(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    if order.status != 'RETURN_REQUESTED':
        messages.error(request, "No return request to verify.")
        return redirect('custom_admin:orders_admin:admin_order_detail', order_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'approve':
            order.status = 'RETURN_PROCESSING'
            messages.success(request, "Return approved.")

        elif action == 'reject':
            order.status = 'DELIVERED'
            order.return_rejection_reason = request.POST.get('reason', '')
            messages.success(request, "Return rejected.")

        order.save()

    return redirect('custom_admin:orders_admin:admin_order_detail', order_id)

@login_required(login_url='custom_admin:login')
@user_passes_test(superuser_check, login_url='custom_admin:login')
@transaction.atomic
def admin_complete_return(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)

    if order.status != 'RETURN_PROCESSING':
        messages.error(request, "Return not in processing state.")
        return redirect('custom_admin:orders_admin:admin_order_detail', order_id)

    # Restock items
    for item in order.items.select_related('variant'):
        if item.variant:
            item.variant.stock += item.quantity
            item.variant.save()

    order.status = 'RETURNED'
    order.save()

    messages.success(request, "Return completed and stock updated.")
    return redirect('custom_admin:orders_admin:admin_order_detail', order_id)

