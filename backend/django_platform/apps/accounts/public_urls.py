from django.urls import path
from .profile_views import ProfilePhotoView, PublicProfilesView

urlpatterns = [
    path("profiles", PublicProfilesView.as_view()),
    path("profiles/<uuid:public_id>", PublicProfilesView.as_view()),
    path("profiles/<uuid:public_id>/photo", ProfilePhotoView.as_view()),
]
