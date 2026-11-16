from django.urls import path
from .views import PushConfigView, SubscriptionView

urlpatterns = [
    path("push/config", PushConfigView.as_view()),
    path("push/subscription", SubscriptionView.as_view()),
]
