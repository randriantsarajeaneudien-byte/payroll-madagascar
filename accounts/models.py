from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SubscriptionPlan(models.TextChoices):
    STANDARD = 'STANDARD', '60 000 Ar / 2 mois'


class Company(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=255, verbose_name="Raison Sociale")
    nif = models.CharField(max_length=50, verbose_name="NIF")
    stat = models.CharField(max_length=50, blank=True, null=True, verbose_name="STAT")
    cnaps_no = models.CharField(max_length=50, verbose_name="N° CNaPS Employeur")
    address = models.TextField(verbose_name="Adresse")
    activity = models.CharField(max_length=255, verbose_name="Activité Principale")

    # --- 1. Gestion des 3 essais gratuits ---
    generation_count = models.IntegerField(default=0, verbose_name="Nombre de fiches générées")
    max_free_generations = models.IntegerField(default=3, verbose_name="Limite d'essais gratuits")

    # --- 2. Abonnement SaaS (60 000 Ar / 2 mois) ---
    plan = models.CharField(
        max_length=20,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.STANDARD,
        verbose_name="Formule d'abonnement"
    )
    subscription_active = models.BooleanField(default=False, verbose_name="Abonnement Actif")
    subscription_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Date d'expiration")

    # --- 3. Sécurité / Bannissement ---
    is_banned = models.BooleanField(default=False, verbose_name="Banni / Suspendu")
    ban_reason = models.TextField(blank=True, null=True, verbose_name="Motif du bannissement")

    def remaining_free_trials(self):
        """Retourne le nombre d'essais gratuits restants"""
        remaining = self.max_free_generations - self.generation_count
        return max(0, remaining)

    def is_subscription_valid(self):
        """Vérifie si l'abonnement est actif et valide dans le temps"""
        if self.is_banned or not self.subscription_active:
            return False
        if self.subscription_expires_at and self.subscription_expires_at < timezone.now():
            return False
        return True

    def can_generate_payslip(self):
        """Vérifie si l'entreprise a le droit de générer un bulletin"""
        if self.is_banned:
            return False
        if self.is_subscription_valid():
            return True
        return self.generation_count < self.max_free_generations

    def __str__(self):
        return self.name


class PaymentSettings(models.Model):
    """Configuration du numéro Mobile Money modifiable depuis l'Admin"""
    mobile_money_number = models.CharField(
        max_length=50,
        default="034 00 000 00",
        verbose_name="Numéro Mobile Money"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=60000,
        verbose_name="Prix de l'abonnement (Ar)"
    )
    instructions = models.TextField(
        default="Veuillez envoyer 60 000 Ar par Mobile Money (pour 2 mois d'accès) avec le nom de votre entreprise en référence.",
        verbose_name="Consignes de paiement"
    )

    class Meta:
        verbose_name = "Configuration Paiement"
        verbose_name_plural = "Configuration Paiement"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton : conserve toujours la même ligne unique en BDD
        super().save(*args, **kwargs)