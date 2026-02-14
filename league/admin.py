"""
Configuration de l'interface admin Django native.
Personnalisation pour GOMA-Efootball League.
"""

from django.contrib import admin
from .models import Team, Match, Result, Standing, AdminProfile, PlayoffMatch


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'player_name', 'gamer_pseudo', 'contact', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'player_name', 'gamer_pseudo']
    list_editable = ['is_active']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'matchday', 'phase', 'is_played']
    list_filter = ['phase', 'matchday', 'is_played']
    search_fields = ['home_team__name', 'away_team__name']


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'home_score', 'away_score', 'validated', 'validated_by']
    list_filter = ['validated']
    list_editable = ['validated']


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ['position', 'team', 'played', 'won', 'drawn', 'lost',
                    'goals_for', 'goals_against', 'goal_difference', 'points']
    ordering = ['-points', '-goal_difference']


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'must_change_password', 'created_at']


@admin.register(PlayoffMatch)
class PlayoffMatchAdmin(admin.ModelAdmin):
    list_display = ['round_type', 'home_team', 'away_team', 'home_score',
                    'away_score', 'is_played', 'has_penalties']
    list_filter = ['round_type', 'is_played']


# Personnaliser le titre de l'admin
admin.site.site_header = "GOMA-Efootball League - Administration"
admin.site.site_title = "GOMA-Efootball"
admin.site.index_title = "Gestion de la compétition"