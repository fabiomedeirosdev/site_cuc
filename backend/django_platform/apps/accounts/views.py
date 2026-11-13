from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.middleware.csrf import get_token, rotate_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, PasswordChangeSerializer, ProfileUpdateSerializer, account_data


@method_decorator([never_cache, csrf_protect], name="dispatch")
class AccountAPIView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "account"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class LoginView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            return Response({"detail": "E-mail ou senha inválidos."}, status=400)
        login(request, user)
        return Response({"user": account_data(user), "csrf_token": get_token(request)})


class LogoutView(AccountAPIView):
    def post(self, request):
        logout(request)
        rotate_token(request)
        return Response({"detail": "Você saiu da sua conta.", "csrf_token": get_token(request)})


class MeView(AccountAPIView):
    def get(self, request):
        return Response(account_data(request.user))

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user.profile, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(account_data(request.user))


@method_decorator(sensitive_post_parameters("current_password", "new_password"), name="dispatch")
class PasswordChangeView(AccountAPIView):
    throttle_scope = "password_change"

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)
        return Response({"detail": "Senha alterada. As outras sessões serão encerradas."})
