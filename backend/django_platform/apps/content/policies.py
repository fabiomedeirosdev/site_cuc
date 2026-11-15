from django.db.models import F, Q

from apps.editorial.models import EditorialGroup, Membership
from apps.editorial.policies import is_editorial_admin, managed_groups
from .models import Article


def author_groups(user):
    if not user.is_authenticated or not user.is_active:
        return EditorialGroup.objects.none()
    if is_editorial_admin(user):
        return EditorialGroup.objects.filter(is_active=True)
    return EditorialGroup.objects.filter(is_active=True, memberships__user=user, memberships__role__in=[Membership.Role.COLUMNIST, Membership.Role.COORDINATOR])


def editable_articles(user):
    if is_editorial_admin(user):
        return Article.objects.all()
    return Article.objects.filter(Q(author=user, group__in=author_groups(user)) | Q(group__in=managed_groups(user)))


def published_articles():
    # A retirada da autorização editorial também retira o conteúdo da leitura pública.
    authorized = Q(author__is_superuser=True) | Q(author__profile__community_role__in=["founder", "developer"]) | Q(group__memberships__user_id=F("author_id"), group__memberships__role__in=[Membership.Role.COLUMNIST, Membership.Role.COORDINATOR])
    return Article.objects.filter(status=Article.Status.PUBLISHED, group__is_active=True, author__is_active=True).filter(authorized).distinct()
