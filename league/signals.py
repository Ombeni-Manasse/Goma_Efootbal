"""
Signals Django pour GOMA-Efootball League.
Gère le recalcul automatique du classement après chaque modification de résultat.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Result, Standing, Team


def recalculate_all_standings():
    """
    Recalcule le classement de TOUTES les équipes.
    Appelé après chaque sauvegarde ou suppression de résultat.
    """
    # S'assurer que chaque équipe a une entrée dans Standing
    for team in Team.objects.filter(is_active=True):
        standing, created = Standing.objects.get_or_create(team=team)
        standing.calculate()

    # Mettre à jour les positions
    standings = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )
    for index, standing in enumerate(standings, 1):
        if standing.position != index:
            standing.position = index
            standing.save(update_fields=['position'])


@receiver(post_save, sender=Result)
def update_standings_on_result_save(sender, instance, **kwargs):
    """
    Signal déclenché après la sauvegarde d'un résultat.
    Recalcule automatiquement le classement.
    """
    if instance.validated:
        recalculate_all_standings()


@receiver(post_delete, sender=Result)
def update_standings_on_result_delete(sender, instance, **kwargs):
    """
    Signal déclenché après la suppression d'un résultat.
    Recalcule automatiquement le classement.
    """
    recalculate_all_standings()


@receiver(post_save, sender=Team)
def create_standing_for_new_team(sender, instance, created, **kwargs):
    """
    Crée automatiquement une entrée Standing pour chaque nouvelle équipe.
    """
    if created:
        Standing.objects.get_or_create(team=instance)