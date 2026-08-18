from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from accounts.models import Company, IRSASetting
from ..models import Payslip

MONTHS_LIST = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]


def _get_declaration_context(request):
    """
    Fonction utilitaire pour extraire la société, appliquer les filtres
    de période (mois/année) et récupérer les fiches de paie correspondantes.
    """
    company = get_object_or_404(Company, owner=request.user)
    selected_month = request.GET.get('month', 'Janvier')

    try:
        selected_year = int(request.GET.get('year', 2026))
    except (ValueError, TypeError):
        selected_year = 2026

    payslips = Payslip.objects.filter(
        employee__company=company,
        month=selected_month,
        year=selected_year,
        is_archived=False
    ).select_related('employee')

    return {
        'company': company,
        'payslips': payslips,
        'months_list': MONTHS_LIST,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }


@login_required
def irsa_declaration_view(request):
    """
    Vue pour l'état récapitulatif de l'IRSA (Impôt sur le Revenu Salarial et Assimilés).
    """
    context = _get_declaration_context(request)
    payslips = context['payslips']

    # Récupération de la configuration IRSA pour l'affichage des paramètres dans le template
    irsa_config = IRSASetting.objects.first()

    context.update({
        'total_gross': sum(p.gross_salary for p in payslips),
        'total_taxable_base': sum(getattr(p, 'taxable_base', p.gross_salary) for p in payslips),
        'total_irsa': sum(p.irsa for p in payslips),
        'irsa_config': irsa_config,
    })

    return render(request, 'payroll/irsa_declaration.html', context)


@login_required
def cnaps_declaration_view(request):
    """
    Vue pour le bordereau de cotisation CNaPS (Caisse Nationale de Prévoyance Sociale).
    """
    context = _get_declaration_context(request)
    payslips = context['payslips']

    total_cnaps_employee = sum(p.cnaps_employee for p in payslips)
    total_cnaps_employer = sum(getattr(p, 'cnaps_employer', 0) for p in payslips)

    context.update({
        'total_cnaps_employee': total_cnaps_employee,
        'total_cnaps_employer': total_cnaps_employer,
        'total_cnaps_due': total_cnaps_employee + total_cnaps_employer,
    })

    return render(request, 'payroll/cnaps_declaration.html', context)


@login_required
def health_declaration_view(request):
    """
    Vue pour la déclaration Médecine du Travail (OSTIE, AMIT, FUNRECO, OSIEM, etc.).
    """
    context = _get_declaration_context(request)
    payslips = context['payslips']

    total_smids_employee = sum(p.smids_employee for p in payslips)
    total_smids_employer = sum(getattr(p, 'smids_employer', 0) for p in payslips)

    context.update({
        'total_smids_employee': total_smids_employee,
        'total_smids_employer': total_smids_employer,
        'total_health_due': total_smids_employee + total_smids_employer,
    })

    return render(request, 'payroll/health_declaration.html', context)