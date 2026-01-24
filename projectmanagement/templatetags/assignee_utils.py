from django import template

register = template.Library()


@register.simple_tag
def task_assignee_stack(task):
    """
    Build a merged, de-duplicated user list from `task.assigned_to` and
    `task.assigned_team.members`, preferring direct assignees first.
    Returns a dict with:
    - users: up to 3 users for avatar display
    - total: total unique users for +N badge
    Assumes relations are prefetched in the view for efficiency.
    """
    users = []
    seen = set()

    try:
        # Direct assignees first
        for u in task.assigned_to.all():
            uid = getattr(u, "id", None)
            if uid is not None and uid not in seen:
                seen.add(uid)
                users.append(u)

        # Then team members not already included
        team = getattr(task, "assigned_team", None)
        if team is not None:
            for u in team.members.all():
                uid = getattr(u, "id", None)
                if uid is not None and uid not in seen:
                    seen.add(uid)
                    users.append(u)
    except Exception:
        # Be resilient to any unexpected attribute errors
        pass

    return {"users": users[:3], "total": len(users)}


@register.simple_tag
def task_assignee_user_list(task):
    """
    Return a merged, de-duplicated list of all users from
    `task.assigned_to` and `task.assigned_team.members`, preferring
    direct assignees first. Useful for text displays (e.g., table view).
    """
    users = []
    seen = set()

    try:
        for u in task.assigned_to.all():
            uid = getattr(u, "id", None)
            if uid is not None and uid not in seen:
                seen.add(uid)
                users.append(u)

        team = getattr(task, "assigned_team", None)
        if team is not None:
            for u in team.members.all():
                uid = getattr(u, "id", None)
                if uid is not None and uid not in seen:
                    seen.add(uid)
                    users.append(u)
    except Exception:
        pass

    return users
