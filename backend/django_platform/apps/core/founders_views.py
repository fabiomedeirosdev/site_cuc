from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import AccountAPIView
from apps.communications.images import clean_communication_image
from .management_views import AdminView
from .media import public_image_url
from .models import FoundersPage


class FoundersSerializer(serializers.ModelSerializer):
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(max_length=50000)
    photo_alt = serializers.CharField(max_length=200)
    photo = serializers.FileField(write_only=True, required=False)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = FoundersPage
        fields = ["title", "body", "photo", "photo_url", "photo_alt", "updated_at"]
        read_only_fields = ["photo_url", "updated_at"]

    def get_photo_url(self, obj):
        return public_image_url(obj.photo)

    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - {"title", "body", "photo", "photo_alt"}:
            raise serializers.ValidationError({"detail": "Informe somente título, história, foto e descrição da foto."})
        return super().to_internal_value(data)

    def validate_photo(self, upload):
        return clean_communication_image(upload)

    def validate(self, attrs):
        if not attrs.get("photo_alt", getattr(self.instance, "photo_alt", "")).strip():
            raise serializers.ValidationError({"photo_alt": "Descreva a foto dos fundadores para quem usa leitor de tela."})
        return attrs


class PublicFoundersView(AccountAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        page = FoundersPage.objects.filter(pk=1).first() or FoundersPage()
        return Response(FoundersSerializer(page).data)


class ManageFoundersView(AdminView):
    def get(self, request):
        page, _ = FoundersPage.objects.get_or_create(pk=1)
        return Response(FoundersSerializer(page).data)

    def patch(self, request):
        page, _ = FoundersPage.objects.get_or_create(pk=1)
        serializer = FoundersSerializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)
