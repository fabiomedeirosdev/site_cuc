from .models import EditorialGroup, Membership


def is_editorial_admin(user):
    from apps.accounts.policies import is_application_admin
    return is_application_admin(user)


def managed_groups(user):
    if not user.is_authenticated or not user.is_active:
        return EditorialGroup.objects.none()
    if is_editorial_admin(user):
        return EditorialGroup.objects.all()
    return EditorialGroup.objects.filter(is_active=True, memberships__user=user, memberships__role=Membership.Role.COORDINATOR)


def can_manage_group(user, group):
    return managed_groups(user).filter(pk=group.pk).exists()


def can_create_groups(user):
    return is_editorial_admin(user) or managed_groups(user).exists()


def public_name(user):
    # Nunca publicar e-mail ou username como alternativa a um nome não preenchido.
    return getattr(getattr(user, "profile", None), "display_name", "") or user.get_full_name() or "Integrante da comunidade"
