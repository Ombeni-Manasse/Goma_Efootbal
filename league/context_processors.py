"""
Context processors personnalisés.
Injecte des variables dans TOUS les templates automatiquement.
"""

from .models import Team, Match, Result


def league_context(request):
    """
    Ajoute des informations globales disponibles dans tous les templates.
    """
    context = {
        'league_name': 'GOMA-Efootball League',
        'whatsapp_link': 'https://chat.whatsapp.com/VOTRE_LIEN_ICI',
        'total_teams': Team.objects.filter(is_active=True).count(),
        'total_matches': Match.objects.count(),
        'matches_played': Match.objects.filter(is_played=True).count(),
    }
    return context