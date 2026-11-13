from django.urls import path

from .views import ManagedGroupsView, MembershipDetailView, MembershipsView, PublicGroupsView, PublicGroupView, PublicColumnistsView


urlpatterns = [
    path("facilitators", PublicColumnistsView.as_view()),
    path("columnists", PublicColumnistsView.as_view()),
    path("groups", PublicGroupsView.as_view()),
    path("groups/<slug:slug>", PublicGroupView.as_view()),
    path("editorial/groups", ManagedGroupsView.as_view()),
    path("editorial/groups/<slug:slug>/members", MembershipsView.as_view()),
    path("editorial/groups/<slug:slug>/members/<int:pk>", MembershipDetailView.as_view()),
]
