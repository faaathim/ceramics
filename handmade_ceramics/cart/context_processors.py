from .models import Cart

def cart_count(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return {'cart_count': cart.items.count()}  # distinct items, not total quantity
    return {'cart_count': 0}