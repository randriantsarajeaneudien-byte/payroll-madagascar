from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, CompanyForm
from .models import Company, PaymentSettings


def register_view(request):
    # Si l'utilisateur est déjà connecté, on l'oriente selon son statut d'entreprise
    if request.user.is_authenticated:
        if Company.objects.filter(owner=request.user).exists():
            return redirect('payroll:dashboard')
        return redirect('accounts:company_create')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('accounts:company_create')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def company_create_view(request):
    # Si l'entreprise existe déjà pour cet utilisateur, rediriger vers le dashboard
    if Company.objects.filter(owner=request.user).exists():
        return redirect('payroll:dashboard')

    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user
            company.save()
            return redirect('payroll:dashboard')
    else:
        form = CompanyForm()

    return render(request, 'accounts/company_form.html', {'form': form})


def custom_logout(request):
    """Gère la déconnexion propre de l'utilisateur"""
    logout(request)
    return redirect('accounts:login')


# --- VUES PAIEMENT & SÉCURITÉ ---

@login_required
def payment_page(request):
    """Page affichée quand la limite des 3 essais est atteinte"""
    company = Company.objects.filter(owner=request.user).first()

    # Si l'entreprise a toujours le droit ou est active, on ne bloque pas
    if company and company.can_generate_payslip() and not company.is_banned:
        return redirect('payroll:dashboard')

    # Récupération de la configuration du numéro Mobile Money et du tarif
    config = PaymentSettings.objects.first()
    if not config:
        config = PaymentSettings.objects.create(
            price=60000,
            instructions="Abonnement de 2 mois donnant un accès illimité à la génération de fiches de paie."
        )

    context = {
        'company': company,
        'mobile_number': config.mobile_money_number,
        'price': config.price,
        'instructions': config.instructions,
    }
    return render(request, 'accounts/payment_page.html', context)


@login_required
def banned_page(request):
    """Page affichée quand l'utilisateur est suspendu/banni"""
    company = Company.objects.filter(owner=request.user).first()

    if company and not company.is_banned:
        return redirect('payroll:dashboard')

    context = {
        'company': company,
        'reason': company.ban_reason if company and company.ban_reason else "Votre accès a été suspendu pour non-respect des conditions d'utilisation."
    }
    return render(request, 'accounts/banned_page.html', context)