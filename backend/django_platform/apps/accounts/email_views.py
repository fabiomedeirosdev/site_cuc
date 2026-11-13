from datetime import timedelta
import hashlib
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.communications.models import NewsletterPreference
from .models import Profile
from .serializers import EmailChangeSerializer, email_change_available
from .views import AccountAPIView


class EmailUnavailable(APIException):
    status_code = 503
    default_detail = "A confirmação de e-mail está temporariamente indisponível. Seu endereço atual foi mantido."


@method_decorator(sensitive_post_parameters("current_password"), name="dispatch")
class EmailChangeView(AccountAPIView):
    throttle_scope = "email_change"

    def post(self, request):
        form = EmailChangeSerializer(data=request.data, context={"request": request})
        form.is_valid(raise_exception=True)
        if not email_change_available():
            raise EmailUnavailable()
        with transaction.atomic():
            profile = Profile.objects.select_for_update().get(user_id=request.user.pk)
            user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(form.validated_data["current_password"]):
                raise serializers.ValidationError({"current_password": "A senha atual está incorreta."})
            token = secrets.token_urlsafe(40)
            profile.pending_email = form.validated_data["new_email"]
            profile.email_change_hash = hashlib.sha256(token.encode()).hexdigest()
            profile.email_change_auth_hash = user.get_session_auth_hash()
            profile.email_change_expires_at = timezone.now() + timedelta(hours=1)
            profile.save(update_fields=["pending_email", "email_change_hash", "email_change_auth_hash", "email_change_expires_at"])
            link = settings.PUBLIC_FRONTEND_URL + "/confirmar-email.html#token=" + token
            try:
                sent = send_mail("Confirme seu novo e-mail na Comunidade Unidos em Cristo", "Confirme a alteração do seu e-mail de acesso:\n\n" + link + "\n\nEste link vence em uma hora. Se não solicitou a alteração, ignore esta mensagem; o e-mail atual será mantido.", settings.DEFAULT_FROM_EMAIL, [profile.pending_email], fail_silently=False)
                if sent != 1:
                    raise RuntimeError("email_unavailable")
            except Exception:
                raise EmailUnavailable()
        return Response({"detail": "Confira o novo endereço de e-mail para confirmar a alteração. O endereço atual continua válido até a confirmação.", "pending_email": profile.pending_email})


@method_decorator(sensitive_post_parameters("token"), name="dispatch")
class EmailConfirmView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "email_change"

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) != {"token"}:
            raise serializers.ValidationError({"detail": "Link inválido ou expirado."})
        token = serializers.CharField(min_length=32, max_length=128).run_validation(request.data["token"])
        digest = hashlib.sha256(token.encode()).hexdigest()
        try:
            with transaction.atomic():
                profile = Profile.objects.select_for_update(of=("self",)).select_related("user").filter(email_change_hash=digest, email_change_expires_at__gt=timezone.now(), user__is_active=True).first()
                if not profile or not profile.pending_email:
                    raise serializers.ValidationError({"detail": "Link inválido ou expirado. Solicite uma nova alteração pelo seu perfil."})
                user = get_user_model().objects.select_for_update().get(pk=profile.user_id)
                if not user.is_active or not constant_time_compare(profile.email_change_auth_hash, user.get_session_auth_hash()):
                    raise serializers.ValidationError({"detail": "Link inválido ou expirado. Solicite uma nova alteração pelo seu perfil."})
                if get_user_model().objects.filter(email__iexact=profile.pending_email).exclude(pk=user.pk).exists():
                    raise serializers.ValidationError({"detail": "Não foi possível usar este endereço. Solicite uma nova alteração pelo seu perfil."})
                user.email = profile.pending_email
                user.save(update_fields=["email"])
                NewsletterPreference.objects.filter(user=user).exclude(email__iexact=user.email).update(user=None, opted_in=False, confirmation_hash="")
                NewsletterPreference.objects.filter(email__iexact=user.email).exclude(user=user).update(user=None)
                profile.pending_email = ""
                profile.email_change_hash = ""
                profile.email_change_auth_hash = ""
                profile.email_change_expires_at = None
                profile.save(update_fields=["pending_email", "email_change_hash", "email_change_auth_hash", "email_change_expires_at"])
        except IntegrityError:
            raise serializers.ValidationError({"detail": "Não foi possível usar este endereço. Solicite uma nova alteração pelo seu perfil."})
        return Response({"detail": "E-mail confirmado e atualizado. Use o novo endereço no próximo login."})
