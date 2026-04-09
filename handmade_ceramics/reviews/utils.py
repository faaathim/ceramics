from orders.models import OrderItem


def can_user_review(user, product):
    return OrderItem.objects.filter(
        order__user=user,
        product=product,
        item_status='DELIVERED'
    ).exists()