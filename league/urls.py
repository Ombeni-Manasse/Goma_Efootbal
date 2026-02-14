"""
Configuration des URLs pour l'application League.
"""

from django.urls import path
from . import views

app_name = 'league'

urlpatterns = [
    # ========================
    # PAGES PUBLIQUES
    # ========================
    path('', views.home, name='home'),
    path('equipes/', views.team_list, name='team_list'),
    path('equipes/<int:pk>/', views.team_detail, name='team_detail'),
    path('calendrier/', views.match_list, name='match_list'),
    path('resultats/', views.result_list, name='result_list'),
    path('classement/', views.standings, name='standings'),
    path('phase-finale/', views.playoffs, name='playoffs'),
    path('reglement/', views.rules, name='rules'),

    # ========================
    # AUTHENTIFICATION
    # ========================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),

    # ========================
    # ADMIN - DASHBOARD
    # ========================
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),

    # ========================
    # ADMIN - ÉQUIPES CRUD
    # ========================
    path('admin-panel/equipe/ajouter/', views.team_create, name='team_create'),
    path('admin-panel/equipe/<int:pk>/modifier/', views.team_edit, name='team_edit'),
    path('admin-panel/equipe/<int:pk>/supprimer/', views.team_delete, name='team_delete'),

    # ========================
    # ADMIN - CALENDRIER
    # ========================
    path('admin-panel/generer-calendrier/', views.generate_calendar, name='generate_calendar'),

    # ========================
    # ADMIN - RÉSULTATS
    # ========================
    path('admin-panel/match/<int:match_id>/resultat/', views.add_result, name='add_result'),
    path('admin-panel/resultat/<int:result_id>/valider/', views.validate_result, name='validate_result'),

    # ========================
    # ADMIN - PHASE FINALE
    # ========================
    path('admin-panel/generer-playoffs/', views.generate_playoffs, name='generate_playoffs'),
    path('admin-panel/playoff/<int:pk>/resultat/', views.playoff_result, name='playoff_result'),

    # ========================
    # ADMIN - GESTION ADMINS
    # ========================
    path('admin-panel/admins/', views.manage_admins, name='manage_admins'),
    path('admin-panel/admins/creer/', views.create_admin, name='create_admin'),
    path('admin-panel/admins/<int:pk>/supprimer/', views.delete_admin, name='delete_admin'),
   


    # ========================
    # API JSON
    # ========================
    path('api/standings/', views.api_standings, name='api_standings'),
    path('api/goals-stats/', views.api_goals_stats, name='api_goals_stats'),
]