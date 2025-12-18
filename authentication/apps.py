# authentication/apps.py

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        # Import and register signals
        try:
            import authentication.signals
            print("Signals imported successfully!")
        except Exception as e:
            print(f"Error importing signals: {e}")