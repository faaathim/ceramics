# my_site/blocked_user_middleware.py
from django.shortcuts import redirect
from django.contrib.auth import logout

class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check if user is authenticated
        if request.user.is_authenticated:
            # If user is blocked
            if getattr(request.user, 'is_blocked', False):
                logout(request)  # Log the user out
                # Redirect explicitly to the user login page using namespace
                return redirect('user_authentication:login')
        response = self.get_response(request)
        return response
