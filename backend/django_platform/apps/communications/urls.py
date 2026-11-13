from django.urls import path
from . import views

urlpatterns = [
    path("communication-images/<str:kind>/<int:pk>", views.CommunicationImageView.as_view()),
    path("events", views.PublicEventsView.as_view()),
    path("mural", views.PublicMuralView.as_view()),
    path("communications/delegation", views.DelegationView.as_view()),
    path("communications/weekly", views.WeeklySettingsView.as_view()),
    path("communications/preview", views.PreviewView.as_view()),
    path("communications/<str:kind>", views.ContentManagementView.as_view()),
    path("communications/<str:kind>/<int:pk>", views.ContentManagementView.as_view()),
    path("newsletter/preference", views.PreferenceView.as_view()),
    path("newsletter/request", views.NewsletterRequestView.as_view()),
    path("newsletter/action", views.NewsletterActionView.as_view()),
]
