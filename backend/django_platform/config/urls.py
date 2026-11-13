from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.views.static import serve


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.accounts.public_urls")),
    path("api/", include("apps.editorial.urls")),
    path("api/", include("apps.content.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/", include("apps.communications.urls")),
]

if settings.DEBUG:
    def development_media(request, path):
        return serve(request, path, document_root=settings.MEDIA_ROOT)

    urlpatterns += [path("media/<path:path>", development_media)]
