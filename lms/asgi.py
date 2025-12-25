import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms.settings")
django_asgi_app = get_asgi_application()

import chate_box.routing  # <-- import after get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from chate_box.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            chate_box.routing.websocket_urlpatterns
        )
    ),
})
