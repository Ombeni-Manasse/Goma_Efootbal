"""
Vues pour GOMA-Efootball League.
Gère toutes les pages et la logique métier.
"""

import random
from itertools import combinations

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Q, Count
from django.http import JsonResponse

from .models import Team, Match, Result, Standing, AdminProfile, PlayoffMatch
from .forms import (
    TeamForm, ResultForm, PlayoffResultForm,
    AdminUserForm, CustomPasswordChangeForm, GenerateCalendarForm
)
from .decorators import admin_required
from .signals import recalculate_all_standings


# ========================
# VUES PUBLIQUES
# ========================

def home(request):
    """
    Page d'accueil - Dashboard avec statistiques générales.
    Accessible à tous.
    """
    teams = Team.objects.filter(is_active=True)
    total_teams = teams.count()
    total_matches = Match.objects.count()
    matches_played = Match.objects.filter(is_played=True).count()
    matches_remaining = total_matches - matches_played

    # Statistiques de buts
    results = Result.objects.filter(validated=True)
    total_goals = 0
    for r in results:
        total_goals += r.home_score + r.away_score

    avg_goals = round(total_goals / matches_played, 2) if matches_played > 0 else 0

    # Top classement (top 5)
    top_standings = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )[:5]

    # Derniers résultats
    last_results = Result.objects.filter(validated=True).order_by('-created_at')[:5]

    # Prochains matchs (non joués)
    next_matches = Match.objects.filter(is_played=False).order_by('matchday')[:5]

    # Meilleur buteur (équipe avec le plus de buts)
    best_attack = Standing.objects.order_by('-goals_for').first()
    best_defense = Standing.objects.order_by('goals_against').first()

    context = {
        'total_teams': total_teams,
        'total_matches': total_matches,
        'matches_played': matches_played,
        'matches_remaining': matches_remaining,
        'total_goals': total_goals,
        'avg_goals': avg_goals,
        'top_standings': top_standings,
        'last_results': last_results,
        'next_matches': next_matches,
        'best_attack': best_attack,
        'best_defense': best_defense,
        'progress': round((matches_played / total_matches * 100), 1) if total_matches > 0 else 0,
    }
    return render(request, 'league/home.html', context)


def team_list(request):
    """
    Liste de toutes les équipes.
    Accessible à tous.
    """
    teams = Team.objects.filter(is_active=True).order_by('name')
    context = {'teams': teams}
    return render(request, 'league/teams/team_list.html', context)


def team_detail(request, pk):
    """
    Détail d'une équipe avec ses statistiques.
    """
    team = get_object_or_404(Team, pk=pk)

    # Récupérer les matchs de l'équipe
    matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team)
    ).order_by('phase', 'matchday')

    # Statistiques
    standing = Standing.objects.filter(team=team).first()

    # Derniers résultats
    results = Result.objects.filter(
        Q(match__home_team=team) | Q(match__away_team=team),
        validated=True
    ).order_by('-created_at')

    # Forme récente (5 derniers matchs)
    form_results = []
    for r in results[:5]:
        if r.match.home_team == team:
            if r.home_score > r.away_score:
                form_results.append('V')
            elif r.home_score == r.away_score:
                form_results.append('N')
            else:
                form_results.append('D')
        else:
            if r.away_score > r.home_score:
                form_results.append('V')
            elif r.away_score == r.home_score:
                form_results.append('N')
            else:
                form_results.append('D')

    context = {
        'team': team,
        'matches': matches,
        'standing': standing,
        'results': results,
        'form_results': form_results,
    }
    return render(request, 'league/teams/team_detail.html', context)


def match_list(request):
    """
    Calendrier des matchs avec filtres.
    Accessible à tous.
    """
    matches = Match.objects.all().order_by('phase', 'matchday')

    # Filtre par équipe
    team_filter = request.GET.get('team')
    if team_filter:
        matches = matches.filter(
            Q(home_team_id=team_filter) | Q(away_team_id=team_filter)
        )

    # Filtre par journée
    matchday_filter = request.GET.get('matchday')
    if matchday_filter:
        matches = matches.filter(matchday=matchday_filter)

    # Filtre par phase
    phase_filter = request.GET.get('phase')
    if phase_filter:
        matches = matches.filter(phase=phase_filter)

    # Obtenir les journées distinctes pour le filtre
    matchdays = Match.objects.values_list('matchday', flat=True).distinct().order_by('matchday')

    # Grouper par journée et phase
    grouped_matches = {}
    for match in matches:
        key = f"{match.get_phase_display()} - Journée {match.matchday}"
        if key not in grouped_matches:
            grouped_matches[key] = []
        grouped_matches[key].append(match)

    teams = Team.objects.filter(is_active=True).order_by('name')

    context = {
        'grouped_matches': grouped_matches,
        'teams': teams,
        'matchdays': matchdays,
        'team_filter': team_filter,
        'matchday_filter': matchday_filter,
        'phase_filter': phase_filter,
    }
    return render(request, 'league/matches/match_list.html', context)


def result_list(request):
    """
    Liste des résultats.
    Accessible à tous.
    """
    results = Result.objects.filter(validated=True).order_by(
        '-match__phase', '-match__matchday'
    )

    # Grouper par journée
    grouped_results = {}
    for result in results:
        key = f"{result.match.get_phase_display()} - Journée {result.match.matchday}"
        if key not in grouped_results:
            grouped_results[key] = []
        grouped_results[key].append(result)

    context = {
        'grouped_results': grouped_results,
    }
    return render(request, 'league/results/result_list.html', context)


def standings(request):
    """
    Page classement.
    Accessible à tous.
    """
    standings_list = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )

    # Mettre à jour les positions
    for index, standing in enumerate(standings_list, 1):
        if standing.position != index:
            standing.position = index
            standing.save(update_fields=['position'])

    # Recharger après mise à jour
    standings_list = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )

    context = {
        'standings': standings_list,
    }
    return render(request, 'league/standings/standings.html', context)


def playoffs(request):
    """
    Page phase finale.
    Accessible à tous.
    """
    playoff_matches = PlayoffMatch.objects.all().order_by('round_type')

    # Séparer par tour
    semi_1 = playoff_matches.filter(round_type__startswith='semi_1')
    semi_2 = playoff_matches.filter(round_type__startswith='semi_2')
    third_place = playoff_matches.filter(round_type='third_place').first()
    final = playoff_matches.filter(round_type='final').first()

    # Top 4 du classement
    top_4 = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )[:4]

    context = {
        'semi_1': semi_1,
        'semi_2': semi_2,
        'third_place': third_place,
        'final': final,
        'top_4': top_4,
        'has_playoffs': playoff_matches.exists(),
    }
    return render(request, 'league/playoffs/playoffs.html', context)


def rules(request):
    """
    Page des règles de la compétition.
    Accessible à tous.
    """
    return render(request, 'league/rules.html')


# ========================
# AUTHENTIFICATION
# ========================

def login_view(request):
    """
    Page de connexion administrateur.
    """
    if request.user.is_authenticated:
        return redirect('league:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Bienvenue, {user.username} !")

            # Vérifier si doit changer le mot de passe
            if hasattr(user, 'admin_profile') and user.admin_profile.must_change_password:
                return redirect('league:change_password')

            return redirect('league:admin_dashboard')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

    return render(request, 'league/login.html')


def logout_view(request):
    """Déconnexion."""
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('league:home')


def change_password(request):
    """
    Page de changement de mot de passe.
    Obligatoire à la première connexion.
    """
    if not request.user.is_authenticated:
        return redirect('league:login')

    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            # Mettre à jour le profil admin
            if hasattr(user, 'admin_profile'):
                user.admin_profile.must_change_password = False
                user.admin_profile.save()

            messages.success(request, "Mot de passe modifié avec succès !")
            return redirect('league:admin_dashboard')
        else:
            messages.error(request, "Erreur lors du changement de mot de passe.")
    else:
        form = CustomPasswordChangeForm(request.user)

    must_change = (
        hasattr(request.user, 'admin_profile')
        and request.user.admin_profile.must_change_password
    )

    context = {
        'form': form,
        'must_change': must_change,
    }
    return render(request, 'league/change_password.html', context)


# ========================
# VUES ADMIN (PROTÉGÉES)
# ========================

@admin_required
def admin_dashboard(request):
    """
    Dashboard administrateur avec toutes les statistiques.
    """
    teams = Team.objects.filter(is_active=True)
    total_teams = teams.count()
    total_matches = Match.objects.count()
    matches_played = Match.objects.filter(is_played=True).count()
    unvalidated_results = Result.objects.filter(validated=False).count()

    # Résultats en attente de validation
    pending_results = Result.objects.filter(validated=False).order_by('-created_at')

    # Stats générales
    results = Result.objects.filter(validated=True)
    total_goals = sum(r.home_score + r.away_score for r in results)

    context = {
        'total_teams': total_teams,
        'total_matches': total_matches,
        'matches_played': matches_played,
        'unvalidated_results': unvalidated_results,
        'pending_results': pending_results,
        'total_goals': total_goals,
        'calendar_generated': total_matches > 0,
    }
    return render(request, 'league/admin_panel/dashboard.html', context)


# --- CRUD Équipes ---


def team_create(request):
    """Créer une nouvelle équipe."""
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.warning(request, "Veuillez vous connecter en tant qu'admin.")
        return redirect('league:login')

    if request.method == 'POST':
        form = TeamForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Équipe créée avec succès !")
            return redirect('league:team_list')
        else:
            messages.error(request, "Erreur dans le formulaire.")
    else:
        form = TeamForm()

    context = {
        'form': form,
        'title': 'Ajouter une équipe',
        'action': 'Créer',
    }
    return render(request, 'league/teams/team_form.html', context)


@admin_required
def team_edit(request, pk):
    """Modifier une équipe existante."""
    team = get_object_or_404(Team, pk=pk)

    if request.method == 'POST':
        form = TeamForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            form.save()
            messages.success(request, f"Équipe '{team.name}' modifiée avec succès !")
            return redirect('league:team_list')
        else:
            messages.error(request, "Erreur dans le formulaire.")
    else:
        form = TeamForm(instance=team)

    context = {
        'form': form,
        'team': team,
        'title': f'Modifier {team.name}',
        'action': 'Enregistrer',
    }
    return render(request, 'league/teams/team_form.html', context)


@admin_required
def team_delete(request, pk):
    """Supprimer une équipe."""
    team = get_object_or_404(Team, pk=pk)

    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f"Équipe '{team_name}' supprimée.")
        return redirect('league:team_list')

    context = {'team': team}
    return render(request, 'league/teams/team_confirm_delete.html', context)


# --- Calendrier ---

@admin_required
def generate_calendar(request):
    """
    Génère automatiquement le calendrier aller-retour.
    Utilise l'algorithme round-robin pour distribuer les matchs en journées.
    """
    if request.method == 'POST':
        form = GenerateCalendarForm(request.POST)
        if form.is_valid():
            # Supprimer l'ancien calendrier
            Match.objects.all().delete()
            Result.objects.all().delete()

            teams = list(Team.objects.filter(is_active=True))
            num_teams = len(teams)

            if num_teams < 2:
                messages.error(request, "Il faut au moins 2 équipes pour générer un calendrier.")
                return redirect('league:generate_calendar')

            # Mélanger si demandé
            if form.cleaned_data.get('shuffle', True):
                random.shuffle(teams)

            # Algorithme Round-Robin
            # Si nombre impair d'équipes, ajouter un "bye" (équipe fictive)
            if num_teams % 2 != 0:
                teams.append(None)  # bye
                num_teams += 1

            num_matchdays = num_teams - 1
            matches_per_day = num_teams // 2

            # Phase ALLER
            schedule = list(teams)
            for matchday in range(1, num_matchdays + 1):
                for i in range(matches_per_day):
                    home = schedule[i]
                    away = schedule[num_teams - 1 - i]

                    # Ignorer les matchs avec "bye" (None)
                    if home is not None and away is not None:
                        Match.objects.create(
                            home_team=home,
                            away_team=away,
                            matchday=matchday,
                            phase='aller'
                        )

                # Rotation : fixer le premier élément, faire tourner les autres
                schedule = [schedule[0]] + [schedule[-1]] + schedule[1:-1]

            # Phase RETOUR (inverser domicile/extérieur)
            aller_matches = Match.objects.filter(phase='aller')
            for match in aller_matches:
                Match.objects.create(
                    home_team=match.away_team,  # Inversé
                    away_team=match.home_team,  # Inversé
                    matchday=match.matchday,
                    phase='retour'
                )

            total = Match.objects.count()
            messages.success(
                request,
                f"Calendrier généré avec succès ! {total} matchs créés "
                f"({total // 2} aller + {total // 2} retour)."
            )

            # Recréer les standings
            Standing.objects.all().delete()
            for team in Team.objects.filter(is_active=True):
                Standing.objects.create(team=team)

            return redirect('league:match_list')
    else:
        form = GenerateCalendarForm()

    teams = Team.objects.filter(is_active=True)
    context = {
        'form': form,
        'teams': teams,
        'team_count': teams.count(),
    }
    return render(request, 'league/matches/generate_calendar.html', context)


# --- Résultats ---

@admin_required
def add_result(request, match_id):
    """
    Ajouter ou modifier le résultat d'un match.
    """
    match = get_object_or_404(Match, pk=match_id)

    # Vérifier si un résultat existe déjà
    try:
        result = match.result
    except Result.DoesNotExist:
        result = None

    if request.method == 'POST':
        if result:
            form = ResultForm(request.POST, instance=result)
        else:
            form = ResultForm(request.POST)

        if form.is_valid():
            result_obj = form.save(commit=False)
            result_obj.match = match
            result_obj.validated = True
            result_obj.validated_by = request.user
            result_obj.save()

            # Marquer le match comme joué
            match.is_played = True
            match.save()

            # Le signal post_save va recalculer le classement automatiquement

            messages.success(
                request,
                f"Résultat enregistré : {match.home_team} {result_obj.home_score} - "
                f"{result_obj.away_score} {match.away_team}"
            )
            return redirect('league:match_list')
    else:
        if result:
            form = ResultForm(instance=result)
        else:
            form = ResultForm()

    context = {
        'form': form,
        'match': match,
        'existing_result': result,
    }
    return render(request, 'league/results/result_form.html', context)


@admin_required
def validate_result(request, result_id):
    """Valider un résultat en attente."""
    result = get_object_or_404(Result, pk=result_id)
    result.validated = True
    result.validated_by = request.user
    result.save()

    messages.success(request, f"Résultat validé : {result}")
    return redirect('league:admin_dashboard')


# --- Phase Finale ---

@admin_required
def generate_playoffs(request):
    """
    Génère la phase finale avec les 4 premiers du classement.
    """
    if request.method == 'POST':
        # Supprimer les anciens matchs de playoff
        PlayoffMatch.objects.all().delete()

        # Récupérer le top 4
        top_4 = Standing.objects.all().order_by(
            '-points', '-goal_difference', '-goals_for'
        )[:4]

        if top_4.count() < 4:
            messages.error(request, "Il faut au moins 4 équipes classées pour générer les playoffs.")
            return redirect('league:playoffs')

        teams = [s.team for s in top_4]

        # Demi-finales : 1er vs 4ème, 2ème vs 3ème
        # Demi-finale 1 : 1er vs 4ème (aller)
        PlayoffMatch.objects.create(
            round_type='semi_1_leg1',
            home_team=teams[0],
            away_team=teams[3]
        )
        # Demi-finale 1 : 4ème vs 1er (retour)
        PlayoffMatch.objects.create(
            round_type='semi_1_leg2',
            home_team=teams[3],
            away_team=teams[0]
        )
        # Demi-finale 2 : 2ème vs 3ème (aller)
        PlayoffMatch.objects.create(
            round_type='semi_2_leg1',
            home_team=teams[1],
            away_team=teams[2]
        )
        # Demi-finale 2 : 3ème vs 2ème (retour)
        PlayoffMatch.objects.create(
            round_type='semi_2_leg2',
            home_team=teams[2],
            away_team=teams[1]
        )
        # Match 3ème place (sera rempli plus tard)
        PlayoffMatch.objects.create(round_type='third_place')
        # Finale (sera rempli plus tard)
        PlayoffMatch.objects.create(round_type='final')

        messages.success(request, "Phase finale générée avec succès !")
        return redirect('league:playoffs')

    return redirect('league:playoffs')


@admin_required
def playoff_result(request, pk):
    """
    Enregistrer le résultat d'un match de phase finale.
    """
    playoff_match = get_object_or_404(PlayoffMatch, pk=pk)

    if request.method == 'POST':
        form = PlayoffResultForm(request.POST, instance=playoff_match)
        if form.is_valid():
            match_obj = form.save(commit=False)
            match_obj.is_played = True
            match_obj.save()

            # Après les demi-finales retour, déterminer les qualifiés
            _update_playoff_bracket(match_obj)

            messages.success(
                request,
                f"Résultat enregistré : {match_obj}"
            )
            return redirect('league:playoffs')
    else:
        form = PlayoffResultForm(instance=playoff_match)

    context = {
        'form': form,
        'playoff_match': playoff_match,
    }
    return render(request, 'league/playoffs/playoff_result_form.html', context)


def _update_playoff_bracket(match_obj):
    """
    Met à jour le bracket des playoffs après un résultat de demi-finale retour.
    Détermine les qualifiés pour la finale et le match 3e place.
    """
    # Vérifier si les deux manches de la demi-finale 1 sont jouées
    semi_1_leg1 = PlayoffMatch.objects.filter(round_type='semi_1_leg1', is_played=True).first()
    semi_1_leg2 = PlayoffMatch.objects.filter(round_type='semi_1_leg2', is_played=True).first()

    semi_2_leg1 = PlayoffMatch.objects.filter(round_type='semi_2_leg1', is_played=True).first()
    semi_2_leg2 = PlayoffMatch.objects.filter(round_type='semi_2_leg2', is_played=True).first()

    finalists = []
    losers = []

    # Déterminer le qualifié de la demi-finale 1
    if semi_1_leg1 and semi_1_leg2:
        winner_1, loser_1 = _determine_semi_winner(semi_1_leg1, semi_1_leg2)
        if winner_1:
            finalists.append(winner_1)
            losers.append(loser_1)

    # Déterminer le qualifié de la demi-finale 2
    if semi_2_leg1 and semi_2_leg2:
        winner_2, loser_2 = _determine_semi_winner(semi_2_leg1, semi_2_leg2)
        if winner_2:
            finalists.append(winner_2)
            losers.append(loser_2)

    # Mettre à jour la finale
    if len(finalists) == 2:
        final = PlayoffMatch.objects.filter(round_type='final').first()
        if final:
            final.home_team = finalists[0]
            final.away_team = finalists[1]
            final.save()

    # Mettre à jour le match 3e place
    if len(losers) == 2:
        third = PlayoffMatch.objects.filter(round_type='third_place').first()
        if third:
            third.home_team = losers[0]
            third.away_team = losers[1]
            third.save()


def _determine_semi_winner(leg1, leg2):
    """
    Détermine le gagnant d'une demi-finale aller-retour.
    Retourne (gagnant, perdant).
    """
    # Calculer le score cumulé
    # leg1 : home_team(A) vs away_team(B)
    # leg2 : home_team(B) vs away_team(A) (inversé)
    team_a = leg1.home_team
    team_b = leg1.away_team

    # Buts de l'équipe A : leg1.home_score + leg2.away_score
    team_a_total = leg1.home_score + leg2.away_score
    # Buts de l'équipe B : leg1.away_score + leg2.home_score
    team_b_total = leg1.away_score + leg2.home_score

    if team_a_total > team_b_total:
        return team_a, team_b
    elif team_b_total > team_a_total:
        return team_b, team_a
    else:
        # En cas d'égalité, vérifier les tirs au but du match retour
        if leg2.has_penalties and leg2.penalty_winner:
            winner = leg2.penalty_winner
            loser = team_b if winner == team_a else team_a
            return winner, loser
        # Si pas de tirs au but définis, la règle des buts à l'extérieur
        # Buts extérieur équipe A = leg2.away_score
        # Buts extérieur équipe B = leg1.away_score
        if leg2.away_score > leg1.away_score:
            return team_a, team_b
        elif leg1.away_score > leg2.away_score:
            return team_b, team_a

    return None, None


# --- Gestion Admins ---

@admin_required
def manage_admins(request):
    """Liste des administrateurs."""
    admins = User.objects.filter(is_staff=True).order_by('username')
    context = {'admins': admins}
    return render(request, 'league/admin_panel/manage_admins.html', context)


@admin_required
def create_admin(request):
    """Créer un nouvel administrateur."""
    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                is_staff=form.cleaned_data.get('is_staff', True)
            )
            # Créer le profil admin
            AdminProfile.objects.create(
                user=user,
                must_change_password=True
            )
            messages.success(
                request,
                f"Administrateur '{user.username}' créé. "
                f"Il devra changer son mot de passe à la première connexion."
            )
            return redirect('league:manage_admins')
    else:
        form = AdminUserForm()

    context = {
        'form': form,
        'title': 'Créer un administrateur',
    }
    return render(request, 'league/admin_panel/admin_form.html', context)


@admin_required
def delete_admin(request, pk):
    """Supprimer un administrateur."""
    user = get_object_or_404(User, pk=pk)

    # Ne pas permettre de se supprimer soi-même
    if user == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('league:manage_admins')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f"Administrateur '{username}' supprimé.")
        return redirect('league:manage_admins')

    context = {'admin_user': user}
    return render(request, 'league/admin_panel/manage_admins.html', context)


# ========================
# API JSON (pour graphiques JS)
# ========================

def api_standings(request):
    """Retourne le classement en JSON pour les graphiques."""
    standings_data = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )
    data = []
    for s in standings_data:
        data.append({
            'team': s.team.name,
            'points': s.points,
            'played': s.played,
            'won': s.won,
            'drawn': s.drawn,
            'lost': s.lost,
            'goals_for': s.goals_for,
            'goals_against': s.goals_against,
            'goal_difference': s.goal_difference,
        })
    return JsonResponse({'standings': data})


def api_goals_stats(request):
    """Retourne les statistiques de buts en JSON."""
    standings_data = Standing.objects.all().order_by('-goals_for')[:10]
    data = {
        'teams': [s.team.name for s in standings_data],
        'goals_for': [s.goals_for for s in standings_data],
        'goals_against': [s.goals_against for s in standings_data],
    }
    return JsonResponse(data)