# user_profile/apps.py
from django.apps import AppConfig

class UserProfileConfig(AppConfig):
    name = 'user_profile'
    verbose_name = 'User Profile'

    def ready(self):
        # import signals to ensure they are registered
        import user_profile.signals  # noqa
