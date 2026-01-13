from .models import Wishlist

def wishlist_data(request):
    if request.user.is_authenticated:
        variant_ids = (
            Wishlist.objects
            .filter(user=request.user)
            .values_list('variant_id', flat=True)
        )
        return {
            'wishlist_variant_ids': set(variant_ids),
            'wishlist_count': len(variant_ids),
        }

    return {
        'wishlist_variant_ids': set(),
        'wishlist_count': 0,
    }
