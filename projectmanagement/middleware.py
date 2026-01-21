class ProjectManagementSystemMiddleware:
    """
    Ensures `current_system` is set to 'projectmanagement' for all projectmanagement views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only set for projectmanagement URLs
        if request.path.startswith('/projectmanagement/'):
            request.current_system = request.session.get('current_system', 'projectmanagement')
            request.session['current_system'] = request.current_system
        else:
            request.current_system = None

        response = self.get_response(request)
        return response