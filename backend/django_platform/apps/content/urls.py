from django.urls import path

from .views import AuthorGroupsView, CoverUploadView, EditorArticlesView, EditorArticleView, PublicArticlesView, PublicArticleView

urlpatterns = [
    path("articles", PublicArticlesView.as_view()),
    path("articles/<int:pk>", PublicArticleView.as_view()),
    path("editorial/author-groups", AuthorGroupsView.as_view()),
    path("editorial/articles", EditorArticlesView.as_view()),
    path("editorial/articles/<int:pk>", EditorArticleView.as_view()),
    path("editorial/covers", CoverUploadView.as_view()),
]
