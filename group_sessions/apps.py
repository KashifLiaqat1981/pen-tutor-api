from django.apps import AppConfig


class GroupSessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'group_sessions'

    def ready(self):
        # Import signals so they get registered
        import group_sessions.signals
