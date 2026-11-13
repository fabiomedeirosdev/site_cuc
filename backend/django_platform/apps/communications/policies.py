from apps.editorial.models import Membership
from apps.editorial.policies import managed_groups, is_editorial_admin
from .models import Delegation


def can_coordinate(user):
    return bool(user and user.is_authenticated and user.is_active and (is_editorial_admin(user) or managed_groups(user).exists()))


def candidates(user):
    return Membership.objects.filter(group__in=managed_groups(user), group__is_active=True, role="columnist", user__is_active=True).exclude(user=user)


def can_manage(user):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if can_coordinate(user):
        return True
    for delegation in Delegation.objects.filter(facilitator=user).select_related("coordinator"):
        if can_coordinate(delegation.coordinator) and candidates(delegation.coordinator).filter(user=user).exists():
            return True
    return False
