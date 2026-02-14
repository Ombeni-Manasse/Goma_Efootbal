"""
Configuration de l'application League.
"""

from django.apps import AppConfig


class LeagueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'league'
    verbose_name = 'GOMA-Efootball League'

    def ready(self):
        """
        Méthode appelée quand l'application est prête.
        Importe les signals pour les activer.
        """
        import league.signals  # noqa: F401