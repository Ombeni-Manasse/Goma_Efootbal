"""
Modèles de données pour GOMA-Efootball League.
Définit les tables : Team, Match, Result, Standing, AdminProfile, PlayoffMatch.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class AdminProfile(models.Model):
    """
    Profil administrateur étendu.
    Lié au modèle User de Django via OneToOneField.
    Gère le flag de première connexion pour forcer le changement de mot de passe.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name="Utilisateur"
    )
    must_change_password = models.BooleanField(
        default=True,
        verbose_name="Doit changer le mot de passe"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    class Meta:
        verbose_name = "Profil Admin"
        verbose_name_plural = "Profils Admin"

    def __str__(self):
        return f"Admin: {self.user.username}"


class Team(models.Model):
    """
    Modèle Équipe.
    Contient toutes les informations d'une équipe participante.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom de l'équipe"
    )
    player_name = models.CharField(
        max_length=100,
        verbose_name="Nom du joueur"
    )
    gamer_pseudo = models.CharField(
        max_length=100,
        verbose_name="Pseudo gamer"
    )
    contact = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Contact (téléphone)"
    )
    logo = models.ImageField(
        upload_to='teams/',
        blank=True,
        null=True,
        verbose_name="Logo de l'équipe"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'inscription"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active"
    )

    class Meta:
        verbose_name = "Équipe"
        verbose_name_plural = "Équipes"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_logo_url(self):
        """Retourne l'URL du logo ou un placeholder."""
        if self.logo:
            return self.logo.url
        return None


class Match(models.Model):
    """
    Modèle Match.
    Représente une rencontre entre deux équipes dans le calendrier.
    """
    PHASE_CHOICES = [
        ('aller', 'Phase Aller'),
        ('retour', 'Phase Retour'),
    ]

    home_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='home_matches',
        verbose_name="Équipe domicile"
    )
    away_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='away_matches',
        verbose_name="Équipe extérieur"
    )
    matchday = models.PositiveIntegerField(
        verbose_name="Journée",
        validators=[MinValueValidator(1)]
    )
    phase = models.CharField(
        max_length=10,
        choices=PHASE_CHOICES,
        default='aller',
        verbose_name="Phase"
    )
    date_played = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Date du match"
    )
    is_played = models.BooleanField(
        default=False,
        verbose_name="Match joué"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    class Meta:
        verbose_name = "Match"
        verbose_name_plural = "Matchs"
        ordering = ['phase', 'matchday', 'id']
        # Empêcher les doublons de match
        unique_together = ['home_team', 'away_team', 'phase']

    def __str__(self):
        return f"J{self.matchday} ({self.get_phase_display()}) : {self.home_team} vs {self.away_team}"


class Result(models.Model):
    """
    Modèle Résultat.
    Stocke le score d'un match joué.
    Lié au match via OneToOneField (un seul résultat par match).
    """
    match = models.OneToOneField(
        Match,
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name="Match"
    )
    home_score = models.PositiveIntegerField(
        default=0,
        verbose_name="Score domicile"
    )
    away_score = models.PositiveIntegerField(
        default=0,
        verbose_name="Score extérieur"
    )
    validated = models.BooleanField(
        default=False,
        verbose_name="Validé par admin"
    )
    validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Validé par"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'enregistrement"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière modification"
    )

    class Meta:
        verbose_name = "Résultat"
        verbose_name_plural = "Résultats"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.match.home_team} {self.home_score} - {self.away_score} {self.match.away_team}"

    @property
    def winner(self):
        """Retourne l'équipe gagnante ou None si match nul."""
        if self.home_score > self.away_score:
            return self.match.home_team
        elif self.away_score > self.home_score:
            return self.match.away_team
        return None


class Standing(models.Model):
    """
    Modèle Classement.
    Calculé automatiquement via les signals Django.
    Une entrée par équipe.
    """
    team = models.OneToOneField(
        Team,
        on_delete=models.CASCADE,
        related_name='standing',
        verbose_name="Équipe"
    )
    played = models.PositiveIntegerField(default=0, verbose_name="Matchs joués")
    won = models.PositiveIntegerField(default=0, verbose_name="Victoires")
    drawn = models.PositiveIntegerField(default=0, verbose_name="Nuls")
    lost = models.PositiveIntegerField(default=0, verbose_name="Défaites")
    goals_for = models.PositiveIntegerField(default=0, verbose_name="Buts marqués")
    goals_against = models.PositiveIntegerField(default=0, verbose_name="Buts encaissés")
    goal_difference = models.IntegerField(default=0, verbose_name="Différence de buts")
    points = models.PositiveIntegerField(default=0, verbose_name="Points")
    position = models.PositiveIntegerField(default=0, verbose_name="Position")

    class Meta:
        verbose_name = "Classement"
        verbose_name_plural = "Classements"
        ordering = ['-points', '-goal_difference', '-goals_for']

    def __str__(self):
        return f"{self.position}. {self.team} - {self.points} pts"

    def calculate(self):
        """
        Recalcule toutes les statistiques de l'équipe
        à partir des résultats validés.
        """
        # Réinitialiser
        self.played = 0
        self.won = 0
        self.drawn = 0
        self.lost = 0
        self.goals_for = 0
        self.goals_against = 0

        # Récupérer tous les résultats validés impliquant cette équipe
        # Matchs à domicile
        home_results = Result.objects.filter(
            match__home_team=self.team,
            validated=True
        )
        for result in home_results:
            self.played += 1
            self.goals_for += result.home_score
            self.goals_against += result.away_score
            if result.home_score > result.away_score:
                self.won += 1
            elif result.home_score == result.away_score:
                self.drawn += 1
            else:
                self.lost += 1

        # Matchs à l'extérieur
        away_results = Result.objects.filter(
            match__away_team=self.team,
            validated=True
        )
        for result in away_results:
            self.played += 1
            self.goals_for += result.away_score
            self.goals_against += result.home_score
            if result.away_score > result.home_score:
                self.won += 1
            elif result.away_score == result.home_score:
                self.drawn += 1
            else:
                self.lost += 1

        # Calculer les totaux
        self.goal_difference = self.goals_for - self.goals_against
        self.points = (self.won * 3) + (self.drawn * 1)
        self.save()


class PlayoffMatch(models.Model):
    """
    Modèle Match de Phase Finale.
    Gère les demi-finales, match 3e place et finale.
    """
    ROUND_CHOICES = [
        ('semi_1_leg1', 'Demi-finale 1 - Aller'),
        ('semi_1_leg2', 'Demi-finale 1 - Retour'),
        ('semi_2_leg1', 'Demi-finale 2 - Aller'),
        ('semi_2_leg2', 'Demi-finale 2 - Retour'),
        ('third_place', 'Match 3ème place'),
        ('final', 'Finale'),
    ]

    round_type = models.CharField(
        max_length=20,
        choices=ROUND_CHOICES,
        verbose_name="Tour"
    )
    home_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='playoff_home',
        verbose_name="Équipe domicile",
        null=True,
        blank=True
    )
    away_team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='playoff_away',
        verbose_name="Équipe extérieur",
        null=True,
        blank=True
    )
    home_score = models.PositiveIntegerField(
        default=0,
        verbose_name="Score domicile"
    )
    away_score = models.PositiveIntegerField(
        default=0,
        verbose_name="Score extérieur"
    )
    is_played = models.BooleanField(
        default=False,
        verbose_name="Match joué"
    )
    has_extra_time = models.BooleanField(
        default=False,
        verbose_name="Prolongations"
    )
    has_penalties = models.BooleanField(
        default=False,
        verbose_name="Tirs au but"
    )
    penalty_winner = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='penalty_wins',
        verbose_name="Vainqueur aux tirs au but"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    class Meta:
        verbose_name = "Match Phase Finale"
        verbose_name_plural = "Matchs Phase Finale"
        ordering = ['round_type']

    def __str__(self):
        home = self.home_team or "TBD"
        away = self.away_team or "TBD"
        return f"{self.get_round_type_display()} : {home} vs {away}"

    @property
    def winner(self):
        """Retourne le gagnant du match (tirs au but inclus)."""
        if not self.is_played:
            return None
        if self.has_penalties and self.penalty_winner:
            return self.penalty_winner
        if self.home_score > self.away_score:
            return self.home_team
        elif self.away_score > self.home_score:
            return self.away_team
        return None