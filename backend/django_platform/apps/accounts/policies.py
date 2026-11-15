from rest_framework.permissions import BasePermission, SAFE_METHODS


ROLE_GROUPS = {"subscriber": "Assinantes", "columnist": "Facilitadores", "coordinator": "Coordenadores"}
CONSUMPTION_PERMISSIONS = {
    "read_articles": "accounts.read_articles",
    "watch_videos": "accounts.watch_videos",
    "listen_audio": "accounts.listen_audio",
}


def is_developer(user):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or getattr(getattr(user, "profile", None), "community_role", "") == "developer"))


def is_application_admin(user):
    return bool(user.is_authenticated and user.is_active and (is_developer(user) or getattr(getattr(user, "profile", None), "community_role", "") == "founder"))


def account_roles(user):
    groups = set(user.groups.values_list("name", flat=True))
    roles = [role for role, group in ROLE_GROUPS.items() if group in groups]
    if is_application_admin(user):
        roles.insert(0, "administrator")
    return roles


def profile_role(user):
    from apps.editorial.policies import managed_groups
    if is_developer(user):
        return "developer", "Desenvolvedor(a)"
    if getattr(getattr(user, "profile", None), "community_role", "") == "founder":
        return "founder", "Fundador(a)"
    if managed_groups(user).exists():
        return "coordinator", "Coordenador(a)"
    if user.editorial_memberships.filter(group__is_active=True, role="columnist").exists():
        return "auxiliary", "Auxiliar"
    if getattr(getattr(user, "profile", None), "community_role", "") == "columnist":
        return "auxiliary", "Facilitador(a)"
    return "subscriber", "Assinante"


def can_publish_phone(user):
    return bool(user.is_authenticated and user.is_active and profile_role(user)[0] in {"developer", "founder", "coordinator"})


def consumption_capabilities(user):
    from apps.content.policies import author_groups
    active = user.is_authenticated and user.is_active
    author = bool(active and author_groups(user).exists())
    return {
        **{key: bool(active and user.has_perm(permission)) for key, permission in CONSUMPTION_PERMISSIONS.items()},
        "create_content": author,
        "edit_content": author,
        "publish_content": author,
        "comment": False,
        "manage_users": bool(active and user.is_staff and user.has_perm("auth.change_user")),
    }


class IsReadOnlyConsumer(BasePermission):
    """Regra de papel; não substitui publicação nem direito de assinatura."""

    def has_permission(self, request, view):
        permission = CONSUMPTION_PERMISSIONS.get(getattr(view, "consumption_capability", ""))
        return bool(
            permission and request.method in SAFE_METHODS and request.user
            and request.user.is_authenticated and request.user.is_active
            and request.user.has_perm(permission)
        )


class HasExclusiveContentAccess(BasePermission):
    """Autorização pelo período pago, consultada em cada requisição."""

    def has_permission(self, request, view):
        from apps.billing.access import has_access
        return has_access(request.user)
