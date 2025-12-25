from urllib.parse import parse_qs
import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from authentication.models import User
from rest_framework_simplejwt.tokens import UntypedToken, AccessToken


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication in WebSockets.
    Expects JWT token as a query param: ws://.../ws/chat/<room_id>/?token=JWT
    """

    async def __call__(self, scope, receive, send):
        # Parse query string
        query_string = parse_qs(scope["query_string"].decode())
        token = query_string.get("token")

        if token:
            try:
                # Validate token
                UntypedToken(token[0])

                # Decode token
                payload = AccessToken(token[0])
                user_id = payload["user_id"]

                # Get user
                user = await database_sync_to_async(User.objects.get)(id=user_id)
                scope['user'] = user
            except Exception:
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
