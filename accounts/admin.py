from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from .models import Company, PaymentSettings


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'owner',
        'generation_count',
        'max_free_generations',
        'subscription_active',
        'subscription_expires_at',
        'is_banned'
    )
    list_filter = ('subscription_active', 'is_banned')
    search_fields = ('name', 'owner__username', 'owner__email', 'nif')

    # Organisation propre dans la fiche d'administration
    fieldsets = (
        ("Informations Générales", {
            'fields': ('owner', 'name', 'nif', 'stat', 'cnaps_no', 'address', 'activity')
        }),
        ("Essais & Limites", {
            'fields': ('generation_count', 'max_free_generations')
        }),
        ("Abonnement SaaS", {
            'fields': ('plan', 'subscription_active', 'subscription_expires_at')
        }),
        ("Sécurité & Bannissement", {
            'fields': ('is_banned', 'ban_reason')
        }),
    )

    actions = ['activate_subscription_1_year', 'ban_company', 'unban_company']

    @admin.action(description="Activer l'abonnement (1 An / 60 000 Ar)")
    def activate_subscription_1_year(self, request, queryset):
        for company in queryset:
            company.subscription_active = True
            company.subscription_expires_at = timezone.now() + timedelta(days=365)
            company.is_banned = False
            company.ban_reason = ""
            company.save()
        self.message_user(request, f"{queryset.count()} entreprise(s) activée(s) pour 1 an avec succès.")

    @admin.action(description="Bannir l'entreprise (Violation des conditions)")
    def ban_company(self, request, queryset):
        queryset.update(
            is_banned=True,
            ban_reason="Votre accès a été suspendu pour non-respect des conditions d'utilisation."
        )
        self.message_user(request, f"{queryset.count()} entreprise(s) bannie(s).")

    @admin.action(description="Débannir l'entreprise")
    def unban_company(self, request, queryset):
        queryset.update(is_banned=False, ban_reason="")
        self.message_user(request, f"{queryset.count()} entreprise(s) débannie(s).")


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('mobile_money_number', 'price')

    def has_add_permission(self, request):
        # Empêche de créer plusieurs configurations de paiement
        if PaymentSettings.objects.exists():
            return False
        return super().has_add_permission(request)