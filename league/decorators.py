"""
Décorateurs personnalisés pour la gestion des accès.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Décorateur qui vérifie que l'utilisateur est un admin connecté.
    Redirige vers la page de login sinon.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Veuillez vous connecter.")
            return redirect('league:login')
        if not request.user.is_staff:
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('league:home')
        # Vérifier si l'admin doit changer son mot de passe
        if hasattr(request.user, 'admin_profile'):
            if request.user.admin_profile.must_change_password:
                # Ne pas rediriger si on est déjà sur la page de changement
                if request.path != '/change-password/':
                    messages.info(
                        request,
                        "Vous devez changer votre mot de passe avant de continuer."
                    )
                    return redirect('league:change_password')
        return view_func(request, *args, **kwargs)
    return wrapper