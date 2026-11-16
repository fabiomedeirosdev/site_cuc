from django.urls import path

from apps.core.views import health, readiness
from .management_views import DashboardView, HighlightView, UsersView, UserAccessView, SubscriptionsView, RequestsView, GroupSettingsView
from .founders_views import ManageFoundersView, PublicFoundersView
from .media import PublicImageView
from .team_views import TeamView
from .notifications import InboxView, NotificationsView


urlpatterns = [
    path("public-images/<path:name>", PublicImageView.as_view()),
    path("notifications", NotificationsView.as_view()),
    path("inbox", InboxView.as_view()),
    path("inbox/<int:pk>", InboxView.as_view()),
    path("management/team", TeamView.as_view()),
    path("management/team/<int:pk>", TeamView.as_view()),
    path("founders", PublicFoundersView.as_view()),
    path("management/founders", ManageFoundersView.as_view()),
    path("management/dashboard", DashboardView.as_view()),
    path("management/highlights", HighlightView.as_view()),
    path("management/highlights/<int:pk>", HighlightView.as_view()),
    path("management/users", UsersView.as_view()),
    path("management/users/<int:pk>", UserAccessView.as_view()),
    path("management/subscriptions", SubscriptionsView.as_view()),
    path("management/requests", RequestsView.as_view()),
    path("management/requests/<uuid:pk>", RequestsView.as_view()),
    path("management/groups", GroupSettingsView.as_view()),
    path("management/groups/<int:pk>", GroupSettingsView.as_view()),
    path("health", health, name="api-health"),
    path("ready", readiness, name="api-readiness"),
]
