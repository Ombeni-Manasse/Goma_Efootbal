"""
Formulaires pour GOMA-Efootball League.
Utilise Django Forms et crispy-forms pour le rendu Bootstrap 5.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from .models import Team, Result, PlayoffMatch


class TeamForm(forms.ModelForm):
    """
    Formulaire pour créer/modifier une équipe.
    """
    class Meta:
        model = Team
        fields = ['name', 'player_name', 'gamer_pseudo', 'contact', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: FC Barcelona'
            }),
            'player_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Jean Dupont'
            }),
            'gamer_pseudo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: xX_ProGamer_Xx'
            }),
            'contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: +243 XXX XXX XXX'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def clean_name(self):
        """Validation personnalisée du nom d'équipe."""
        name = self.cleaned_data.get('name')
        if len(name) < 2:
            raise forms.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return name


class ResultForm(forms.ModelForm):
    """
    Formulaire pour enregistrer le résultat d'un match.
    """
    class Meta:
        model = Result
        fields = ['home_score', 'away_score']
        widgets = {
            'home_score': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg text-center',
                'min': '0',
                'max': '99',
                'style': 'font-size: 2rem; font-weight: bold;'
            }),
            'away_score': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg text-center',
                'min': '0',
                'max': '99',
                'style': 'font-size: 2rem; font-weight: bold;'
            }),
        }


class PlayoffResultForm(forms.ModelForm):
    """
    Formulaire pour les résultats de phase finale.
    Inclut les options prolongations et tirs au but.
    """
    class Meta:
        model = PlayoffMatch
        fields = [
            'home_score', 'away_score',
            'has_extra_time', 'has_penalties', 'penalty_winner'
        ]
        widgets = {
            'home_score': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg text-center',
                'min': '0',
                'max': '99',
                'style': 'font-size: 2rem; font-weight: bold;'
            }),
            'away_score': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg text-center',
                'min': '0',
                'max': '99',
                'style': 'font-size: 2rem; font-weight: bold;'
            }),
            'has_extra_time': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'has_penalties': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limiter les choix du penalty_winner aux deux équipes du match
        if self.instance and self.instance.pk:
            teams = Team.objects.filter(
                pk__in=[self.instance.home_team_id, self.instance.away_team_id]
            )
            self.fields['penalty_winner'].queryset = teams
            self.fields['penalty_winner'].widget = forms.Select(attrs={
                'class': 'form-select'
            })
            self.fields['penalty_winner'].required = False


class AdminUserForm(forms.Form):
    """
    Formulaire pour créer un nouvel administrateur.
    """
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Nom d'utilisateur"
        }),
        label="Nom d'utilisateur"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        }),
        label="Mot de passe"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        }),
        label="Confirmer le mot de passe"
    )
    is_staff = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Accès staff"
    )

    def clean_username(self):
        """Vérifie que le nom d'utilisateur n'existe pas déjà."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur existe déjà.")
        return username

    def clean(self):
        """Vérifie que les mots de passe correspondent."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Formulaire de changement de mot de passe personnalisé avec Bootstrap.
    """
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ancien mot de passe'
        }),
        label="Ancien mot de passe"
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe'
        }),
        label="Nouveau mot de passe"
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le nouveau mot de passe'
        }),
        label="Confirmer le nouveau mot de passe"
    )


class GenerateCalendarForm(forms.Form):
    """
    Formulaire de confirmation pour générer le calendrier.
    """
    confirm = forms.BooleanField(
        required=True,
        label="Je confirme vouloir générer le calendrier",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    shuffle = forms.BooleanField(
        required=False,
        initial=True,
        label="Mélanger aléatoirement les confrontations",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )