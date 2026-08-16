from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from accounts.models import Company
from ..models import Employee, Payslip


@login_required
def dashboard(request):
    """
    Tableau de bord principal RH & Paie :
    Affiche les salariés de l'entreprise et les récents bulletins non archivés.
    """
    company = get_object_or_404(Company, owner=request.user)

    # Récupération des salariés de l'entreprise
    employees = Employee.objects.filter(company=company).order_by('last_name', 'first_name')

    # Filtrage et recherche des bulletins récents non masqués
    search_query = request.GET.get('q', '').strip()
    recent_payslips = Payslip.objects.filter(
        employee__company=company,
        is_archived=False
    ).select_related('employee')

    if search_query:
        recent_payslips = recent_payslips.filter(
            Q(employee__last_name__icontains=search_query) |
            Q(employee__first_name__icontains=search_query) |
            Q(month__icontains=search_query) |
            Q(year__icontains=search_query)
        )

    recent_payslips = recent_payslips.order_by('-year', '-created_at')[:30]

    context = {
        'company': company,
        'employees': employees,
        'recent_payslips': recent_payslips,
        'search_query': search_query,
    }
    return render(request, 'payroll/dashboard.html', context)


@login_required
def toggle_hide_payslip(request, payslip_id):
    """
    Masque ou réaffiche une fiche de paie (bascule du champ is_archived).
    """
    company = get_object_or_404(Company, owner=request.user)
    payslip = get_object_or_404(Payslip, id=payslip_id, employee__company=company)

    payslip.is_archived = not payslip.is_archived
    payslip.save()

    if payslip.is_archived:
        messages.success(request, f"La fiche de paie de {payslip.employee.first_name} a été masquée.")
        return redirect('payroll:dashboard')
    else:
        messages.success(request, f"La fiche de paie de {payslip.employee.first_name} a été réaffichée.")
        return redirect('payroll:archived_payslips')


@login_required
def archived_payslips(request):
    """
    Affiche la liste des fiches de paie masquées / archivées.
    """
    company = get_object_or_404(Company, owner=request.user)
    archived_payslips_list = Payslip.objects.filter(
        employee__company=company,
        is_archived=True
    ).select_related('employee').order_by('-year', '-created_at')

    context = {
        'company': company,
        'archived_payslips': archived_payslips_list,
    }
    return render(request, 'payroll/archived_payslips.html', context)