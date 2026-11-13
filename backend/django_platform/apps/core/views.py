from django.conf import settings
from django.db import DatabaseError, connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    environment = "development" if settings.DEBUG else "production"
    return Response({"status": "ok", "environment": environment})


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return Response({"status": "unavailable", "database": "unavailable"}, status=503)
    return Response({"status": "ok", "database": "ok"})
