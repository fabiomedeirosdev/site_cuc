from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Preserva o usuário Django existente e autentica somente por e-mail."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)
        if not isinstance(email, str) or password is None:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email.strip())
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Executa o hash também para contas inexistentes, como no ModelBackend.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
