"""
Configuration des URLs principales du projet GOMA-Efootball League.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin Django natif (pour accès direct si besoin)
    path('django-admin/', admin.site.urls),
    # Notre application
    path('', include('league.urls')),
]

# Servir les fichiers media en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)