from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from .models import Company, PaymentSettings, IRSASetting


@admin.action(description="Activer l'abonnement (2 mois / 60 000 Ar)")
def activate_subscription_2_months(modeladmin, request, queryset):
    for company in queryset:
        company.subscription_active = True
        company.subscription_expires_at = timezone.now() + timedelta(days=60)
        company.is_banned = False
        company.ban_reason = ""
        company.save()
    modeladmin.message_user(request, f"{queryset.count()} entreprise(s) activée(s) pour 2 mois.")


@admin.action(description="Réinitialiser les essais gratuits (Remettre à 0)")
def reset_free_trials(modeladmin, request, queryset):
    queryset.update(generation_count=0)
    modeladmin.message_user(request, f"Essais gratuits réinitialisés pour {queryset.count()} entreprise(s).")


@admin.action(description="Bannir l'entreprise")
def ban_company(modeladmin, request, queryset):
    queryset.update(
        is_banned=True,
        ban_reason="Votre accès a été suspendu pour non-respect des conditions d'utilisation."
    )
    modeladmin.message_user(request, f"{queryset.count()} entreprise(s) bannie(s).")


@admin.action(description="Débannir l'entreprise")
def unban_company(modeladmin, request, queryset):
    queryset.update(is_banned=False, ban_reason="")
    modeladmin.message_user(request, f"{queryset.count()} entreprise(s) débannie(s).")


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

    actions = [
        activate_subscription_2_months,
        reset_free_trials,
        ban_company,
        unban_company,
    ]


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('mobile_money_number', 'price')

    def has_add_permission(self, request):
        if PaymentSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(IRSASetting)
class IRSASettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'minimum_irsa', 'child_deduction_amount')

    def has_add_permission(self, request):
        if IRSASetting.objects.exists():
            return False
        return super().has_add_permission(request)