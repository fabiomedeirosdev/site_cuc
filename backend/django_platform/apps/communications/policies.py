from apps.editorial.models import Membership
from apps.editorial.policies import managed_groups, is_editorial_admin
from .models import Delegation


def can_coordinate(user):
    return bool(user and user.is_authenticated and user.is_active and (is_editorial_admin(user) or user.profile.community_role == "administration" or managed_groups(user).exists()))


def candidates(user):
    return Membership.objects.filter(group__in=managed_groups(user), group__is_active=True, role="columnist", user__is_active=True).exclude(user=user)


def can_delegate(user):
    return is_editorial_admin(user)


def facilitator_users():
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    return get_user_model().objects.filter(is_active=True).filter(Q(profile__community_role__in=["columnist", "priest", "deacon"]) | Q(editorial_memberships__role="columnist", editorial_memberships__group__is_active=True)).distinct()


def can_manage(user, kind=None):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if can_coordinate(user):
        return True
    for delegation in Delegation.objects.filter(facilitator=user).select_related("coordinator"):
        valid = (is_editorial_admin(delegation.coordinator) and facilitator_users().filter(pk=user.pk).exists()) or (can_coordinate(delegation.coordinator) and candidates(delegation.coordinator).filter(user=user).exists())
        flags = {"events": delegation.can_edit_agenda, "notices": delegation.can_edit_mural, "campaigns": delegation.can_edit_newsletter}
        if valid and (flags.get(kind, False) if kind else any(flags.values())):
            return True
    return False
