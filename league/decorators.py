"""
Décorateurs personnalisés pour la gestion des accès.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Vérifie que l'utilisateur est un admin connecté.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Vérifier si connecté
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter.")
            return redirect('league:login')

        # Vérifier si staff
        if not request.user.is_staff:
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('league:home')

        # Vérifier changement mot de passe obligatoire
        try:
            profile = request.user.admin_profile
            if profile.must_change_password:
                if 'change-password' not in request.path:
                    return redirect('league:change_password')
        except Exception:
            # Pas de profil admin, on laisse passer
            pass

        return view_func(request, *args, **kwargs)
    return wrapper