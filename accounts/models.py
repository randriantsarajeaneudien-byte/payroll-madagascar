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


class IRSASetting(models.Model):
    """Modèle pour contrôler les paramètres du barème IRSA depuis l'Admin"""
    name = models.CharField(max_length=100, default="Paramètres IRSA Madagascar")
    minimum_irsa = models.DecimalField(max_digits=10, decimal_places=2, default=3000.00,
                                       verbose_name="Minimum de perception (Ar)")
    child_deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00,
                                                 verbose_name="Déduction par enfant (Ar)")

    # Seuils des tranches
    tranche_1_limit = models.DecimalField(max_digits=10, decimal_places=2, default=350000.00,
                                          verbose_name="Limite Tranche 1 (Ar)")
    tranche_2_limit = models.DecimalField(max_digits=10, decimal_places=2, default=400000.00,
                                          verbose_name="Limite Tranche 2 (Ar)")
    tranche_3_limit = models.DecimalField(max_digits=10, decimal_places=2, default=500000.00,
                                          verbose_name="Limite Tranche 3 (Ar)")
    tranche_4_limit = models.DecimalField(max_digits=10, decimal_places=2, default=600000.00,
                                          verbose_name="Limite Tranche 4 (Ar)")
    tranche_5_limit = models.DecimalField(max_digits=10, decimal_places=2, default=4000000.00,
                                          verbose_name="Limite Tranche 5 (Ar)")

    class Meta:
        verbose_name = "Configuration IRSA"
        verbose_name_plural = "Configuration IRSA"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton : une seule ligne de config IRSA
        super().save(*args, **kwargs)


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
        self.pk = 1  # Singleton
        super().save(*args, **kwargs)