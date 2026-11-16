from .models import EditorialGroup, Membership


def is_editorial_admin(user):
    from apps.accounts.policies import is_application_admin
    return is_application_admin(user)


def managed_groups(user):
    if not user.is_authenticated or not user.is_active:
        return EditorialGroup.objects.none()
    if is_editorial_admin(user):
        return EditorialGroup.objects.all()
    if getattr(user.profile, "community_role", "") == "administration":
        return EditorialGroup.objects.filter(is_active=True, memberships__user=user)
    return EditorialGroup.objects.filter(is_active=True, memberships__role=Membership.Role.COORDINATOR, memberships__user=user)


def can_manage_group(user, group):
    return managed_groups(user).filter(pk=group.pk).exists()


def can_create_groups(user):
    return is_editorial_admin(user) or (user.is_authenticated and user.is_active and user.profile.community_role == "administration") or managed_groups(user).exists()


def public_name(user):
    if user is None:
        return "Integrante excluído"
    # Nunca publicar e-mail ou username como alternativa a um nome não preenchido.
    return getattr(getattr(user, "profile", None), "display_name", "") or user.get_full_name() or "Integrante da comunidade"
