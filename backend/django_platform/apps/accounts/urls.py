from django.urls import path

from .views import CsrfView, LoginView, LogoutView, MeView, PasswordChangeView
from .email_views import EmailChangeView, EmailConfirmView


urlpatterns = [
    path("email", EmailChangeView.as_view()),
    path("email/confirm", EmailConfirmView.as_view()),
    path("csrf", CsrfView.as_view(), name="auth-csrf"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("password", PasswordChangeView.as_view(), name="auth-password"),
]
