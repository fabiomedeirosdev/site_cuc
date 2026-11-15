from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.views import AccountAPIView
from .images import clean_cover
from .models import CoverImage
from .policies import author_groups, editable_articles, published_articles
from .serializers import ArticleEditorSerializer, ArticleReadSerializer, ArticleSummarySerializer, ArticleWriteSerializer


def with_relations(queryset):
    return queryset.select_related("author__profile", "group", "cover")


@method_decorator(never_cache, name="dispatch")
class PublicArticlesView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArticleSummarySerializer

    def get_queryset(self):
        queryset = published_articles()
        if self.request.query_params.get("featured") == "1":
            queryset = queryset.filter(is_featured=True).order_by("featured_position", "-published_at", "-pk")
        if self.request.query_params.get("group"):
            queryset = queryset.filter(group__slug=self.request.query_params["group"])
        if self.request.query_params.get("q"):
            queryset = queryset.filter(title__icontains=self.request.query_params["q"][:200])
        return with_relations(queryset)


@method_decorator(never_cache, name="dispatch")
class PublicArticleView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ArticleReadSerializer

    def get_queryset(self):
        return with_relations(published_articles())


class EditorArticlesView(AccountAPIView):
    def get(self, request):
        from rest_framework.pagination import PageNumberPagination
        queryset = with_relations(editable_articles(request.user)).order_by("-updated_at", "-pk")
        paginator = PageNumberPagination()
        return paginator.get_paginated_response(ArticleEditorSerializer(paginator.paginate_queryset(queryset, request, view=self), many=True).data)

    def post(self, request):
        if not author_groups(request.user).exists():
            raise PermissionDenied("Somente facilitadores e coordenadores autorizados pela coordenação podem criar conteúdo.")
        serializer = ArticleWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        article = serializer.save(author=request.user)
        return Response(ArticleEditorSerializer(article).data, status=201)


class EditorArticleView(AccountAPIView):
    def get_object(self, request, pk):
        return get_object_or_404(with_relations(editable_articles(request.user)), pk=pk)

    def get(self, request, pk):
        return Response(ArticleEditorSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk):
        article = self.get_object(request, pk)
        serializer = ArticleWriteSerializer(article, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(ArticleEditorSerializer(serializer.save()).data)

    def delete(self, request, pk):
        self.get_object(request, pk).delete()
        return Response(status=204)


class AuthorGroupsView(AccountAPIView):
    def get(self, request):
        return Response(list(author_groups(request.user).values("id", "name", "slug")))


class CoverUploadView(AccountAPIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not author_groups(request.user).exists():
            raise PermissionDenied("Somente facilitadores e coordenadores autorizados podem enviar fotos.")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Escolha uma foto de capa."})
        cover = CoverImage.objects.create(owner=request.user, file=clean_cover(upload))
        return Response({"id": str(cover.pk), "url": cover.file.url}, status=201)
