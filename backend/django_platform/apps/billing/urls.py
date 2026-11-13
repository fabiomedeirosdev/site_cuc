from django.urls import path

from .views import BillingConfigView, CancelSubscriptionView, CheckoutView, CompleteRegistrationView, ConsumerRequestView, InvitationCheckView, MySubscriptionsView, PagBankWebhookView, ResendInvitationView

urlpatterns = [
    path("billing/config", BillingConfigView.as_view()),
    path("billing/checkout", CheckoutView.as_view()),
    path("billing/webhooks/pagbank", PagBankWebhookView.as_view()),
    path("billing/invitation/check", InvitationCheckView.as_view()),
    path("billing/invitation/complete", CompleteRegistrationView.as_view()),
    path("billing/invitation/resend", ResendInvitationView.as_view()),
    path("billing/mine", MySubscriptionsView.as_view()),
    path("billing/subscriptions/<uuid:pk>/cancel", CancelSubscriptionView.as_view()),
    path("billing/subscriptions/<uuid:pk>/requests", ConsumerRequestView.as_view()),
]
