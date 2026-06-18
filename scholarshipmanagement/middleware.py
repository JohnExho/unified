"""
System-aware middleware for Scholarship Management login redirect.
"""
from django.shortcuts import redirect


class ScholarshipSystemMiddleware:
    """Sets current_system on the request for scholarship management routes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/scholarshipmanagement/'):
            request.current_system = 'scholarshipmanagement'
        response = self.get_response(request)
        return response
