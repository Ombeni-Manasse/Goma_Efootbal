"""
Commande Django pour créer le compte admin par défaut.
Username: efootball
Password: 1234
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from league.models import AdminProfile


class Command(BaseCommand):
    help = 'Crée le compte administrateur par défaut (efootball/1234)'

    def handle(self, *args, **options):
        username = 'efootball'
        password = '1234'

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"L'utilisateur '{username}' existe déjà.")
            )
            return

        # Créer le superutilisateur
        user = User.objects.create_superuser(
            username=username,
            password=password,
            email='admin@goma-efootball.com'
        )

        # Créer le profil admin avec obligation de changer le mot de passe
        AdminProfile.objects.create(
            user=user,
            must_change_password=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Compte admin créé avec succès !\n"
                f"   Username: {username}\n"
                f"   Password: {password}\n"
                f"   ⚠️  Le mot de passe devra être changé à la première connexion."
            )
        )