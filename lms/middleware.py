# Import the necessary modules for custom middleware
from django.http import Http404
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class GlobalErrorHandlerMiddleware:
    """
    A middleware to catch and handle exceptions globally.

    This middleware is responsible for catching all exceptions that occur
    during the request/response cycle and returning a standardized error
    response to the client.

    The middleware catches exceptions from both API views and non-API
    views and returns a Response object with a JSON payload containing
    information about the error.

    The middleware also logs the exception using the Python logging module
    and provides additional information about the exception.

    :param get_response: A callable that returns the response for the request
    :type get_response: callable
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Calls the get_response callable to get the response for the request.

        :param request: The request object
        :type request: django.http.HttpRequest
        :return: The response object
        :rtype: django.http.HttpResponse
        """
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Handles exceptions that occur during the request/response cycle.

        This method is responsible for catching all exceptions that occur
        during the request/response cycle and returning a standardized error
        response to the client.

        The method catches exceptions from both API views and non-API
        views and returns a Response object with a JSON payload containing
        information about the error.

        The method also logs the exception using the Python logging module
        and provides additional information about the exception.

        :param request: The request object
        :type request: django.http.HttpRequest
        :param exception: The exception object
        :type exception: Exception
        :return: The response object
        :rtype: django.http.HttpResponse
        """
        # Use DRF's exception handler for API views
        response = exception_handler(exception, {'request': request})
        if response is not None:
            # Handle DRF responses (JSON or TemplateResponse)
            if hasattr(response, 'data'):  # JSONRenderer case
                return Response({
                    'success': False,
                    'message': response.data.get('detail', str(exception)),
                    'errors': response.data if isinstance(response.data, dict) else None
                }, status=response.status_code)
            return response  # Return TemplateResponse as-is (BrowsableAPIRenderer)

        # Handle non-API exceptions
        if isinstance(exception, Http404):
            logger.warning(f"Not found: {str(exception)}", exc_info=True)
            return Response({
                'success': False,
                'message': 'Resource not found.',
                'errors': None
            }, status=status.HTTP_404_NOT_FOUND)

        logger.error(f"Unhandled exception: {str(exception)}", exc_info=True)
        return Response({
            'success': False,
            'message': 'An unexpected error occurred. Please try again later.',
            'errors': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
