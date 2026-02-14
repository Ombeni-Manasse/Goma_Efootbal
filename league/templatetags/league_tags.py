"""
Tags de template personnalisés pour GOMA-Efootball League.
"""

from django import template

register = template.Library()


@register.filter
def subtract(value, arg):
    """Soustraction dans les templates : {{ value|subtract:arg }}"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calcule un pourcentage : {{ value|percentage:total }}"""
    try:
        if int(total) == 0:
            return 0
        return round((int(value) / int(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def get_badge_class(position):
    """Retourne la classe CSS du badge selon la position au classement."""
    try:
        pos = int(position)
        if pos == 1:
            return 'bg-warning text-dark'  # Or
        elif pos == 2:
            return 'bg-secondary'  # Argent
        elif pos == 3:
            return 'bg-danger'  # Bronze
        elif pos <= 4:
            return 'bg-success'  # Qualifié playoffs
        else:
            return 'bg-dark'
    except (ValueError, TypeError):
        return 'bg-dark'