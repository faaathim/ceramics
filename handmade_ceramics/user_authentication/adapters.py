from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):

        # If user is already logged in, link accounts normally.
        if request.user.is_authenticated:
            sociallogin.connect(request, request.user)
            return

        # If this social account is already linked, do nothing.
        if sociallogin.is_existing:
            return

        # Get email from Google response
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return  # No email, cannot link

        try:
            # Try to find existing user with this email
            user = User.objects.get(email=email)

            # Link social login to this existing user
            sociallogin.connect(request, user)
            return

        except User.DoesNotExist:
            # User does NOT exist → let allauth create a new one properly
            return
