from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from accounts.models import Company
from ..models import Employee, Payslip, PayrollSettings
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

    company = payslip.employee.company
    payroll_settings, created = PayrollSettings.objects.get_or_create(company=company)

    return render(request, 'payroll/payslip_detail.html', {
        'payslip': payslip,
        'payroll_settings': payroll_settings,
        'cnaps_emp_pct': int(payroll_settings.cnaps_employee_rate * 100),
        'smids_emp_pct': int(payroll_settings.smids_employee_rate * 100),
    })


@login_required
def payslip_create(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id, company__owner=request.user)
    company = employee.company

    if request.method == 'POST':
        form = PayslipCreateForm(request.POST)
        if form.is_valid():
            payslip = form.save(commit=False)
            payslip.employee = employee

            # 1. Retenue pour absence
            payslip.unpaid_absences_amount = (payslip.absence_days or 0) * (payslip.daily_absence_rate or 0)

            # 2. Calculs automatiques des cotisations et de l'IRSA (avec les taux de l'entreprise)
            calc = calculate_madagascar_payroll(
                base_salary=employee.base_salary,
                unpaid_absences=payslip.unpaid_absences_amount,
                overtime=payslip.overtime_amount or 0,
                bonus=payslip.bonuses or 0,
                advance=payslip.advances or 0,
                children=employee.children_count or 0,
                company=company
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

            # 5. Incrémentation du compteur de générations
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

            # Calcul avec les taux personnalisés de l'entreprise
            calc = calculate_madagascar_payroll(
                base_salary=employee.base_salary,
                unpaid_absences=0,
                overtime=0,
                bonus=0,
                advance=0,
                children=employee.children_count or 0,
                company=company
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


@login_required
def generate_payslip_pdf(request, payslip_id):
    payslip = get_object_or_404(Payslip, id=payslip_id, employee__company__owner=request.user)

    company = payslip.employee.company
    payroll_settings, created = PayrollSettings.objects.get_or_create(company=company)

    cnaps_emp_pct = int(payroll_settings.cnaps_employee_rate * 100)
    smids_emp_pct = int(payroll_settings.smids_employee_rate * 100)

    response = HttpResponse(content_type='application/pdf')
    response[
        'Content-Disposition'] = f'inline; filename="bulletin_{payslip.employee.last_name}_{payslip.month}_{payslip.year}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # En-tête du PDF
    elements.append(Paragraph(f"<b>BULLETIN DE PAIE - {payslip.month.upper()} {payslip.year}</b>", styles['Heading1']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Entreprise :</b> {company.name}", styles['Normal']))

    job_title = payslip.employee.job_title if payslip.employee.job_title else 'Salarié'
    elements.append(
        Paragraph(f"<b>Salarié :</b> {payslip.employee.first_name} {payslip.employee.last_name} ({job_title})",
                  styles['Normal']))
    elements.append(Spacer(1, 15))

    # Tableau du PDF
    data = [
        ["Désignation", "Gains (Ar)", "Retenues (Ar)"],
        ["Salaire de base", f"{payslip.employee.base_salary:,.2f}", "-"],
    ]

    if payslip.unpaid_absences_amount > 0:
        data.append([f"Absences ({payslip.absence_days} j)", "-", f"{payslip.unpaid_absences_amount:,.2f}"])
    if payslip.overtime_amount > 0:
        data.append(["Heures supplémentaires", f"{payslip.overtime_amount:,.2f}", "-"])
    if payslip.bonuses > 0:
        data.append(["Primes & Indemnités", f"{payslip.bonuses:,.2f}", "-"])

    data.append(["TOTAL BRUT", f"{payslip.gross_salary:,.2f}", "-"])
    data.append([f"CNaPS ({cnaps_emp_pct}%)", "-", f"{payslip.cnaps_employee:,.2f}"])
    data.append([f"Sanitaire / SMIDS ({smids_emp_pct}%)", "-", f"{payslip.smids_employee:,.2f}"])
    data.append(["IRSA", "-", f"{payslip.irsa:,.2f}"])

    if payslip.advances > 0:
        data.append(["Retenue sur Avance", "-", f"{payslip.advances:,.2f}"])

    data.append(["NET À PAYER", f"{payslip.net_payable:,.2f}", ""])

    t = Table(data, colWidths=[230, 140, 140])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(t)
    doc.build(elements)
    return response