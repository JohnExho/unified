from typing import Optional

from .models import SystemMembership


class Services:

    @staticmethod
    def has_access(user, system_name: str, role: Optional[str] = None) -> bool:
        """Return True if `user` is a member of `system_name`.

        If `role` is provided, the membership must match that role.
        """
        if user is None:
            return False

        try:
            qs = SystemMembership.objects.filter(user=user, system_name=system_name)
            if role:
                qs = qs.filter(system_role=role)
            return qs.exists()
        except Exception:
            # If models are not available or query fails, deny access by default
            return False
