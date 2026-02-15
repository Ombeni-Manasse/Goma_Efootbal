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
from .signals import recalculate_all_standings


def is_admin(request):
    """Vérifie si l'utilisateur est un admin connecté."""
    return request.user.is_authenticated and request.user.is_staff


# ========================
# VUES PUBLIQUES
# ========================

def home(request):
    """Page d'accueil - Dashboard avec statistiques générales."""
    teams = Team.objects.filter(is_active=True)
    total_teams = teams.count()
    total_matches = Match.objects.count()
    matches_played = Match.objects.filter(is_played=True).count()
    matches_remaining = total_matches - matches_played

    results = Result.objects.filter(validated=True)
    total_goals = 0
    for r in results:
        total_goals += r.home_score + r.away_score

    avg_goals = round(total_goals / matches_played, 2) if matches_played > 0 else 0

    top_standings = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )[:5]

    last_results = Result.objects.filter(validated=True).order_by('-created_at')[:5]
    next_matches = Match.objects.filter(is_played=False).order_by('matchday')[:5]
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
    """Liste de toutes les équipes."""
    teams = Team.objects.filter(is_active=True).order_by('name')
    context = {'teams': teams}
    return render(request, 'league/teams/team_list.html', context)


def team_detail(request, pk):
    """Détail d'une équipe avec ses statistiques."""
    team = get_object_or_404(Team, pk=pk)

    matches = Match.objects.filter(
        Q(home_team=team) | Q(away_team=team)
    ).order_by('phase', 'matchday')

    standing = Standing.objects.filter(team=team).first()

    results = Result.objects.filter(
        Q(match__home_team=team) | Q(match__away_team=team),
        validated=True
    ).order_by('-created_at')

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
    """Calendrier des matchs avec filtres."""
    matches = Match.objects.all().order_by('phase', 'matchday')

    team_filter = request.GET.get('team')
    if team_filter:
        matches = matches.filter(
            Q(home_team_id=team_filter) | Q(away_team_id=team_filter)
        )

    matchday_filter = request.GET.get('matchday')
    if matchday_filter:
        matches = matches.filter(matchday=matchday_filter)

    phase_filter = request.GET.get('phase')
    if phase_filter:
        matches = matches.filter(phase=phase_filter)

    # Filtre matchs non joués seulement
    status_filter = request.GET.get('status')
    if status_filter == 'pending':
        matches = matches.filter(is_played=False)
    elif status_filter == 'played':
        matches = matches.filter(is_played=True)

    matchdays = Match.objects.values_list('matchday', flat=True).distinct().order_by('matchday')

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
        'status_filter': status_filter,
    }
    return render(request, 'league/matches/match_list.html', context)


def result_list(request):
    """Liste des résultats."""
    results = Result.objects.filter(validated=True).order_by(
        '-match__phase', '-match__matchday'
    )

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
    """Page classement."""
    standings_list = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )

    for index, standing in enumerate(standings_list, 1):
        if standing.position != index:
            standing.position = index
            standing.save(update_fields=['position'])

    standings_list = Standing.objects.all().order_by(
        '-points', '-goal_difference', '-goals_for'
    )

    context = {
        'standings': standings_list,
    }
    return render(request, 'league/standings/standings.html', context)


def playoffs(request):
    """Page phase finale."""
    playoff_matches = PlayoffMatch.objects.all().order_by('round_type')

    semi_1 = playoff_matches.filter(round_type__startswith='semi_1')
    semi_2 = playoff_matches.filter(round_type__startswith='semi_2')
    third_place = playoff_matches.filter(round_type='third_place').first()
    final = playoff_matches.filter(round_type='final').first()

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
    """Page des règles."""
    return render(request, 'league/rules.html')


# ========================
# AUTHENTIFICATION
# ========================

def login_view(request):
    """Page de connexion administrateur."""
    if request.user.is_authenticated:
        return redirect('league:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Bienvenue, {user.username} !")

            try:
                if user.admin_profile.must_change_password:
                    return redirect('league:change_password')
            except Exception:
                pass

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
    """Page de changement de mot de passe."""
    if not request.user.is_authenticated:
        return redirect('league:login')

    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            try:
                user.admin_profile.must_change_password = False
                user.admin_profile.save()
            except Exception:
                pass

            messages.success(request, "Mot de passe modifié avec succès !")
            return redirect('league:admin_dashboard')
        else:
            messages.error(request, "Erreur lors du changement de mot de passe.")
    else:
        form = CustomPasswordChangeForm(request.user)

    must_change = False
    try:
        must_change = request.user.admin_profile.must_change_password
    except Exception:
        pass

    context = {
        'form': form,
        'must_change': must_change,
    }
    return render(request, 'league/change_password.html', context)


# ========================
# VUES ADMIN (PROTÉGÉES)
# ========================

def admin_dashboard(request):
    """Dashboard administrateur."""
    if not is_admin(request):
        messages.warning(request, "Veuillez vous connecter en tant qu'admin.")
        return redirect('league:login')

    teams = Team.objects.filter(is_active=True)
    total_teams = teams.count()
    total_matches = Match.objects.count()
    matches_played = Match.objects.filter(is_played=True).count()
    matches_not_played = Match.objects.filter(is_played=False).count()
    unvalidated_results = Result.objects.filter(validated=False).count()

    pending_results = Result.objects.filter(validated=False).order_by('-created_at')

    results = Result.objects.filter(validated=True)
    total_goals = sum(r.home_score + r.away_score for r in results)

    # Matchs non joués pour ajout rapide de résultats
    unplayed_matches = Match.objects.filter(is_played=False).order_by('phase', 'matchday')[:10]

    context = {
        'total_teams': total_teams,
        'total_matches': total_matches,
        'matches_played': matches_played,
        'matches_not_played': matches_not_played,
        'unvalidated_results': unvalidated_results,
        'pending_results': pending_results,
        'total_goals': total_goals,
        'calendar_generated': total_matches > 0,
        'unplayed_matches': unplayed_matches,
    }
    return render(request, 'league/admin_panel/dashboard.html', context)


# --- CRUD Équipes ---

def team_create(request):
    """Créer une nouvelle équipe."""
    if not is_admin(request):
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


def team_edit(request, pk):
    """Modifier une équipe existante."""
    if not is_admin(request):
        return redirect('league:login')

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


def team_delete(request, pk):
    """Supprimer une équipe."""
    if not is_admin(request):
        return redirect('league:login')

    team = get_object_or_404(Team, pk=pk)

    if request.method == 'POST':
        team_name = team.name
        team.delete()
        messages.success(request, f"Équipe '{team_name}' supprimée.")
        return redirect('league:team_list')

    context = {'team': team}
    return render(request, 'league/teams/team_confirm_delete.html', context)


# --- Calendrier ---

def generate_calendar(request):
    """Génère automatiquement le calendrier aller-retour."""
    if not is_admin(request):
        return redirect('league:login')

    if request.method == 'POST':
        form = GenerateCalendarForm(request.POST)
        if form.is_valid():
            Match.objects.all().delete()
            Result.objects.all().delete()

            teams = list(Team.objects.filter(is_active=True))
            num_teams = len(teams)

            if num_teams < 2:
                messages.error(request, "Il faut au moins 2 équipes.")
                return redirect('league:generate_calendar')

            if form.cleaned_data.get('shuffle', True):
                random.shuffle(teams)

            if num_teams % 2 != 0:
                teams.append(None)
                num_teams += 1

            num_matchdays = num_teams - 1
            matches_per_day = num_teams // 2

            schedule = list(teams)
            for matchday in range(1, num_matchdays + 1):
                for i in range(matches_per_day):
                    home = schedule[i]
                    away = schedule[num_teams - 1 - i]

                    if home is not None and away is not None:
                        Match.objects.create(
                            home_team=home,
                            away_team=away,
                            matchday=matchday,
                            phase='aller'
                        )

                schedule = [schedule[0]] + [schedule[-1]] + schedule[1:-1]

            aller_matches = Match.objects.filter(phase='aller')
            for match in aller_matches:
                Match.objects.create(
                    home_team=match.away_team,
                    away_team=match.home_team,
                    matchday=match.matchday,
                    phase='retour'
                )

            total = Match.objects.count()
            messages.success(
                request,
                f"Calendrier généré ! {total} matchs créés."
            )

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

def add_result(request, match_id):
    """Ajouter ou modifier le résultat d'un match."""
    if not is_admin(request):
        messages.warning(request, "Veuillez vous connecter en tant qu'admin.")
        return redirect('league:login')

    match = get_object_or_404(Match, pk=match_id)

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

            match.is_played = True
            match.save()

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


def validate_result(request, result_id):
    """Valider un résultat en attente."""
    if not is_admin(request):
        return redirect('league:login')

    result = get_object_or_404(Result, pk=result_id)
    result.validated = True
    result.validated_by = request.user
    result.save()

    messages.success(request, f"Résultat validé : {result}")
    return redirect('league:admin_dashboard')


# --- Phase Finale ---

def generate_playoffs(request):
    """Génère la phase finale avec les 4 premiers du classement."""
    if not is_admin(request):
        return redirect('league:login')

    if request.method == 'POST':
        PlayoffMatch.objects.all().delete()

        top_4 = Standing.objects.all().order_by(
            '-points', '-goal_difference', '-goals_for'
        )[:4]

        if top_4.count() < 4:
            messages.error(request, "Il faut au moins 4 équipes classées.")
            return redirect('league:playoffs')

        teams = [s.team for s in top_4]

        PlayoffMatch.objects.create(
            round_type='semi_1_leg1',
            home_team=teams[0],
            away_team=teams[3]
        )
        PlayoffMatch.objects.create(
            round_type='semi_1_leg2',
            home_team=teams[3],
            away_team=teams[0]
        )
        PlayoffMatch.objects.create(
            round_type='semi_2_leg1',
            home_team=teams[1],
            away_team=teams[2]
        )
        PlayoffMatch.objects.create(
            round_type='semi_2_leg2',
            home_team=teams[2],
            away_team=teams[1]
        )
        PlayoffMatch.objects.create(round_type='third_place')
        PlayoffMatch.objects.create(round_type='final')

        messages.success(request, "Phase finale générée avec succès !")
        return redirect('league:playoffs')

    return redirect('league:playoffs')


def playoff_result(request, pk):
    """Enregistrer le résultat d'un match de phase finale."""
    if not is_admin(request):
        return redirect('league:login')

    playoff_match = get_object_or_404(PlayoffMatch, pk=pk)

    if request.method == 'POST':
        form = PlayoffResultForm(request.POST, instance=playoff_match)
        if form.is_valid():
            match_obj = form.save(commit=False)
            match_obj.is_played = True
            match_obj.save()

            _update_playoff_bracket(match_obj)

            messages.success(request, f"Résultat enregistré : {match_obj}")
            return redirect('league:playoffs')
    else:
        form = PlayoffResultForm(instance=playoff_match)

    context = {
        'form': form,
        'playoff_match': playoff_match,
    }
    return render(request, 'league/playoffs/playoff_result_form.html', context)


def _update_playoff_bracket(match_obj):
    """Met à jour le bracket des playoffs après un résultat."""
    semi_1_leg1 = PlayoffMatch.objects.filter(round_type='semi_1_leg1', is_played=True).first()
    semi_1_leg2 = PlayoffMatch.objects.filter(round_type='semi_1_leg2', is_played=True).first()
    semi_2_leg1 = PlayoffMatch.objects.filter(round_type='semi_2_leg1', is_played=True).first()
    semi_2_leg2 = PlayoffMatch.objects.filter(round_type='semi_2_leg2', is_played=True).first()

    finalists = []
    losers = []

    if semi_1_leg1 and semi_1_leg2:
        winner_1, loser_1 = _determine_semi_winner(semi_1_leg1, semi_1_leg2)
        if winner_1:
            finalists.append(winner_1)
            losers.append(loser_1)

    if semi_2_leg1 and semi_2_leg2:
        winner_2, loser_2 = _determine_semi_winner(semi_2_leg1, semi_2_leg2)
        if winner_2:
            finalists.append(winner_2)
            losers.append(loser_2)

    if len(finalists) == 2:
        final = PlayoffMatch.objects.filter(round_type='final').first()
        if final:
            final.home_team = finalists[0]
            final.away_team = finalists[1]
            final.save()

    if len(losers) == 2:
        third = PlayoffMatch.objects.filter(round_type='third_place').first()
        if third:
            third.home_team = losers[0]
            third.away_team = losers[1]
            third.save()


def _determine_semi_winner(leg1, leg2):
    """Détermine le gagnant d'une demi-finale aller-retour."""
    team_a = leg1.home_team
    team_b = leg1.away_team

    team_a_total = leg1.home_score + leg2.away_score
    team_b_total = leg1.away_score + leg2.home_score

    if team_a_total > team_b_total:
        return team_a, team_b
    elif team_b_total > team_a_total:
        return team_b, team_a
    else:
        if leg2.has_penalties and leg2.penalty_winner:
            winner = leg2.penalty_winner
            loser = team_b if winner == team_a else team_a
            return winner, loser
        if leg2.away_score > leg1.away_score:
            return team_a, team_b
        elif leg1.away_score > leg2.away_score:
            return team_b, team_a

    return None, None


# --- Gestion Admins ---

def manage_admins(request):
    """Liste des administrateurs."""
    if not is_admin(request):
        return redirect('league:login')

    admins = User.objects.filter(is_staff=True).order_by('username')
    context = {'admins': admins}
    return render(request, 'league/admin_panel/manage_admins.html', context)


def create_admin(request):
    """Créer un nouvel administrateur."""
    if not is_admin(request):
        return redirect('league:login')

    if request.method == 'POST':
        form = AdminUserForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                is_staff=form.cleaned_data.get('is_staff', True)
            )
            AdminProfile.objects.create(
                user=user,
                must_change_password=True
            )
            messages.success(
                request,
                f"Administrateur '{user.username}' créé."
            )
            return redirect('league:manage_admins')
    else:
        form = AdminUserForm()

    context = {
        'form': form,
        'title': 'Créer un administrateur',
    }
    return render(request, 'league/admin_panel/admin_form.html', context)


def delete_admin(request, pk):
    """Supprimer un administrateur."""
    if not is_admin(request):
        return redirect('league:login')

    user = get_object_or_404(User, pk=pk)

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
# API JSON
# ========================

def api_standings(request):
    """Retourne le classement en JSON."""
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