from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.models import Company
from ..models import Employee, Payslip
from ..forms import PayslipCreateForm
from ..utils.calculations import calculate_madagascar_payroll


@login_required
def payslip_list(request):
    company = get_object_or_404(Company, owner=request.user)
    payslips = Payslip.objects.filter(employee__company=company, is_archived=False).order_by('-created_at')
    return render(request, 'payroll/payslip_list.html', {'payslips': payslips})


@login_required
def payslip_detail(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id, employee__company__owner=request.user)
    return render(request, 'payroll/payslip_detail.html', {'payslip': payslip})


@login_required
def payslip_create(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id, company__owner=request.user)
    if request.method == 'POST':
        form = PayslipCreateForm(request.POST)
        if form.is_valid():
            payslip = form.save(commit=False)
            payslip.employee = employee

            # 1. Retenue pour absence
            payslip.unpaid_absences_amount = (payslip.absence_days or 0) * (payslip.daily_absence_rate or 0)

            # 2. Calculs automatiques des cotisations et de l'IRSA
            calc = calculate_madagascar_payroll(
                base_salary=employee.base_salary,
                unpaid_absences=payslip.unpaid_absences_amount,
                overtime=payslip.overtime_amount or 0,
                bonus=payslip.bonuses or 0,
                advance=payslip.advances or 0,
                children=employee.children_count or 0
            )
            payslip.gross_salary = calc['gross_salary']
            payslip.cnaps_employee = calc['cnaps_employee']
            payslip.smids_employee = calc['smids_employee']
            payslip.taxable_base = calc['taxable_base']
            payslip.irsa = calc['irsa']
            payslip.net_payable = calc['net_payable']
            payslip.cnaps_employer = calc['cnaps_employer']
            payslip.smids_employer = calc['smids_employer']
            payslip.fmfp_employer = calc['fmfp_employer']
            payslip.save()

            # 3. Mise à jour du solde de l'avance du salarié
            if payslip.advances > 0 and employee.total_advance_balance > 0:
                employee.total_advance_balance = max(0, employee.total_advance_balance - payslip.advances)

            # 4. Mise à jour du solde de congés payés restants
            paid_leave = getattr(payslip, 'paid_leave_days', 0) or 0
            if paid_leave > 0 and getattr(employee, 'leave_balance', 0) > 0:
                employee.leave_balance = max(0, employee.leave_balance - paid_leave)

            employee.save()

            # 5. Incrementation du compteur de générations
            company = employee.company
            if company:
                company.generation_count += 1
                company.save()

            messages.success(request, f"Bulletin généré avec succès pour {employee.first_name} {employee.last_name}.")
            return redirect('payroll:payslip_detail', payslip_id=payslip.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous.")
    else:
        default_daily_rate = round(employee.base_salary / 30, 2) if employee.base_salary else 0
        form = PayslipCreateForm(initial={
            'year': 2026,
            'working_days': 30,
            'daily_absence_rate': default_daily_rate
        })
    return render(request, 'payroll/payslip_form.html', {'form': form, 'employee': employee})


@login_required
def payslip_bulk_create(request):
    """Génération groupée des fiches de paie pour tous les salariés de l'entreprise"""
    company = get_object_or_404(Company, owner=request.user)
    employees = Employee.objects.filter(company=company)

    if request.method == 'POST':
        month = request.POST.get('month')
        year = int(request.POST.get('year', 2026))

        if not month:
            messages.error(request, "Veuillez sélectionner un mois.")
            return redirect('payroll:payslip_bulk_create')

        count = 0
        for employee in employees:
            default_daily_rate = round(employee.base_salary / 30, 2) if employee.base_salary else 0
            calc = calculate_madagascar_payroll(
                base_salary=employee.base_salary,
                unpaid_absences=0,
                overtime=0,
                bonus=0,
                advance=0,
                children=employee.children_count or 0
            )
            Payslip.objects.create(
                employee=employee,
                month=month,
                year=year,
                working_days=30,
                absence_days=0,
                paid_leave_days=0,
                daily_absence_rate=default_daily_rate,
                unpaid_absences_amount=0,
                overtime_hours=0,
                overtime_amount=0,
                bonuses=0,
                advances=0,
                gross_salary=calc['gross_salary'],
                cnaps_employee=calc['cnaps_employee'],
                smids_employee=calc['smids_employee'],
                taxable_base=calc['taxable_base'],
                irsa=calc['irsa'],
                net_payable=calc['net_payable'],
                cnaps_employer=calc['cnaps_employer'],
                smids_employer=calc['smids_employer'],
                fmfp_employer=calc['fmfp_employer']
            )
            count += 1

        if count > 0:
            company.generation_count += count
            company.save()

        messages.success(request, f"{count} bulletin(s) généré(s) avec succès pour {month} {year}.")
        return redirect('payroll:dashboard')

    months_list = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    context = {
        'employees': employees,
        'months_list': months_list,
        'current_year': 2026
    }
    return render(request, 'payroll/payslip_bulk_form.html', context)


@login_required
def toggle_hide_payslip(request, payslip_id):
    """Bascule le statut masqué / affiché d'un bulletin de paie"""
    payslip = get_object_or_404(Payslip, id=payslip_id, employee__company__owner=request.user)
    payslip.is_archived = not payslip.is_archived
    payslip.save()

    status_msg = "masqué" if payslip.is_archived else "restauré"
    messages.info(request, f"Le bulletin de paie a été {status_msg}.")
    return redirect('payroll:dashboard')


@login_required
def archived_payslips(request):
    """Affiche la liste des fiches de paie masquées / archivées"""
    company = get_object_or_404(Company, owner=request.user)
    archived_list = Payslip.objects.filter(employee__company=company, is_archived=True).order_by('-created_at')

    return render(request, 'payroll/archived_payslips.html', {
        'archived_payslips': archived_list
    })


# À ajouter dans payroll/views/payslip_views.py

@login_required
def generate_payslip_pdf(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id, employee__company__owner=request.user)

    response = HttpResponse(content_type='application/pdf')
    response[
        'Content-Disposition'] = f'inline; filename="bulletin_{payslip.employee.last_name}_{payslip.month}_{payslip.year}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()

    # Structure du bulletin PDF
    elements.append(Paragraph(f"<b>BULLETIN DE PAIE - {payslip.month.upper()} {payslip.year}</b>", styles['Heading1']))
    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(f"<b>Employé :</b> {payslip.employee.first_name} {payslip.employee.last_name}", styles['Normal']))
    elements.append(Paragraph(f"<b>Salaire Brut :</b> {payslip.gross_salary:,.2f} Ar", styles['Normal']))
    elements.append(Paragraph(f"<b>Net à Payer :</b> {payslip.net_payable:,.2f} Ar", styles['Normal']))

    doc.build(elements)
    return response