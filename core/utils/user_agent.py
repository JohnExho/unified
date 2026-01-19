def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')
