from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import Company
from payroll.models import PayrollSettings
from payroll.forms import PayrollSettingsForm


@login_required
def payroll_settings_view(request):
    # Récupération sécurisée de l'entreprise associée à l'utilisateur connecté
    company = get_object_or_404(Company, owner=request.user)

    # Récupère ou crée les paramètres de paie pour cette entreprise
    settings_obj, created = PayrollSettings.objects.get_or_create(company=company)

    if request.method == 'POST':
        form = PayrollSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            return redirect('payroll:payroll_settings')  # Redirection avec namespace
    else:
        form = PayrollSettingsForm(instance=settings_obj)

    context = {
        'form': form,
    }
    return render(request, 'payroll/payroll_settings.html', context)