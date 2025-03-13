"""Core application views module.

This module contains the main views for the March Madness application,
including the home page and health endpoint.
"""

import logging

from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def home(request):
    """Render the home page.

    Args:
        request: Django request object

    Returns:
        HttpResponse: Rendered home page template
    """
    return render(request, "index.html")


def health(_request):
    """Health check endpoint.

    Used to verify API availability and system status.

    Args:
        _request: Django request object (unused)

    Returns:
        JsonResponse: Status information
    """
    logger.debug("Health check requested")
    return JsonResponse({"status": "ok", "version": "1.0.0"})
