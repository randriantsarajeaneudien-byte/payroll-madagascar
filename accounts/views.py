from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage

from .forms import RegisterForm, CompanyForm
from .models import Company, PaymentSettings
from .tokens import account_activation_token

User = get_user_model()


def register_view(request):
    """Inscription des nouveaux utilisateurs avec confirmation par e-mail (Double Opt-In)"""
    if request.user.is_authenticated:
        if Company.objects.filter(owner=request.user).exists():
            return redirect('payroll:dashboard')
        return redirect('accounts:company_create')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Désactivé jusqu'à la confirmation par e-mail
            user.save()

            # Préparation de l'e-mail de confirmation
            current_site = get_current_site(request)
            mail_subject = "Activez votre compte Payroll Madagascar"
            message = render_to_string('accounts/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })

            email = EmailMessage(
                subject=mail_subject,
                body=message,
                to=[user.email]
            )
            email.content_subtype = "html"  # Envoi au format HTML
            email.send()

            messages.success(
                request,
                "Un e-mail de confirmation a été envoyé à votre adresse. "
                "Veuillez cliquer sur le lien qu'il contient pour activer votre compte."
            )
            return redirect('accounts:login')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def activate(request, uidb64, token):
    """Vue de validation du token de confirmation d'e-mail"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(
            request,
            "Votre compte a été activé avec succès ! Vous pouvez maintenant vous connecter."
        )
        return redirect('accounts:login')
    else:
        messages.error(
            request,
            "Le lien d'activation est invalide ou a déjà été utilisé."
        )
        return redirect('accounts:login')


@login_required
def company_create_view(request):
    """Création de l'entreprise initiale pour l'utilisateur"""
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
    """Déconnexion sécurisée utilisable en GET ou POST"""
    logout(request)
    return redirect('accounts:login')


# --- VUES PAIEMENT & SÉCURITÉ ---

@login_required
def payment_page(request):
    """Page affichée quand le quota des 3 essais est dépassé"""
    company = Company.objects.filter(owner=request.user).first()

    # Si l'entreprise a un abonnement valide ou des essais restants, pas de blocage
    if company and company.can_generate_payslip() and not company.is_banned:
        return redirect('payroll:dashboard')

    # Récupération de la configuration Mobile Money
    config = PaymentSettings.objects.first()
    if not config:
        config = PaymentSettings.objects.create(
            price=60000,
            instructions="Veuillez envoyer 60 000 Ar par Mobile Money (pour 2 mois d'accès) avec le nom de votre entreprise en référence."
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
    """Page d'affichage en cas de suspension ou bannissement"""
    company = Company.objects.filter(owner=request.user).first()

    if company and not company.is_banned:
        return redirect('payroll:dashboard')

    context = {
        'company': company,
        'reason': company.ban_reason if company and company.ban_reason else "Votre accès a été suspendu pour non-respect des conditions d'utilisation."
    }
    return render(request, 'accounts/banned_page.html', context)