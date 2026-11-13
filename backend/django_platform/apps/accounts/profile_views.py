from django.http import FileResponse, Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.editorial.models import Membership
from .models import Profile
from .serializers import PublicProfileSerializer
from .views import AccountAPIView


class PublicProfilesView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, public_id=None):
        profiles = Profile.objects.filter(user__is_active=True).select_related("user").order_by("-updated_at", "pk")
        if public_id is not None:
            return Response(PublicProfileSerializer(get_object_or_404(profiles, public_id=public_id)).data)
        query = request.query_params.get("q", "").strip()[:150]
        if query:
            profiles = profiles.filter(Q(display_name__icontains=query) | Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query))
        role = request.query_params.get("role", "")
        coordinators = Membership.objects.filter(group__is_active=True, role="coordinator").values("user_id")
        auxiliaries = Membership.objects.filter(group__is_active=True, role="columnist").values("user_id")
        if role == "developer":
            profiles = profiles.filter(user__is_superuser=True)
        elif role == "coordinator":
            profiles = profiles.filter(user_id__in=coordinators, user__is_superuser=False)
        elif role == "auxiliary":
            profiles = profiles.filter(user_id__in=auxiliaries, user__is_superuser=False).exclude(user_id__in=coordinators)
        elif role == "subscriber":
            profiles = profiles.filter(user__is_superuser=False).exclude(user_id__in=coordinators).exclude(user_id__in=auxiliaries)
        elif role:
            raise ValidationError({"role": "Escolha uma função válida."})
        paginator = PageNumberPagination()
        rows = paginator.paginate_queryset(profiles, request)
        return paginator.get_paginated_response(PublicProfileSerializer(rows, many=True).data)


class ProfilePhotoView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, public_id):
        profile = get_object_or_404(Profile, public_id=public_id, user__is_active=True)
        if not profile.avatar:
            raise Http404
        try:
            response = FileResponse(profile.avatar.open("rb"), content_type="image/webp")
        except FileNotFoundError:
            raise Http404
        response["X-Content-Type-Options"] = "nosniff"
        return response
