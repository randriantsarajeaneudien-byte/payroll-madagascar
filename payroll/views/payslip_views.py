from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from accounts.models import Company
from ..models import Employee, Payslip, PayrollSettings
from ..forms import PayslipCreateForm
from ..utils.calculations import calculate_madagascar_payroll, calculate_attendance_deductions_for_month


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
def api_calculate_attendance(request):
    """API JSON pour actualiser les absences et le taux journalier selon le mois/année sélectionnés"""
    employee_id = request.GET.get('employee_id')
    month = request.GET.get('month')
    year_str = request.GET.get('year')

    if not employee_id or not month or not year_str:
        return JsonResponse({'error': 'Paramètres manquants'}, status=400)

    try:
        year = int(year_str)
    except ValueError:
        return JsonResponse({'error': 'Année invalide'}, status=400)

    employee = get_object_or_404(Employee, id=employee_id, company__owner=request.user)
    att_data = calculate_attendance_deductions_for_month(employee, month, year)

    return JsonResponse({
        'absence_days': att_data['absence_days'],
        'daily_absence_rate': att_data['daily_absence_rate'],
        'unpaid_absences_amount': att_data['unpaid_absences_amount']
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

            # 1. Récupération automatique des absences et congés sans solde du mois
            att_data = calculate_attendance_deductions_for_month(employee, payslip.month, payslip.year)
            payslip.absence_days = att_data['absence_days']
            payslip.daily_absence_rate = att_data['daily_absence_rate']
            payslip.unpaid_absences_amount = att_data['unpaid_absences_amount']

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
        # Valeurs par défaut pour le chargement initial (ex: Janvier 2026)
        default_month = "Janvier"
        default_year = 2026

        # Calcul automatique direct des absences pour pré-remplir les champs
        att_data = calculate_attendance_deductions_for_month(employee, default_month, default_year)

        # Utilisation de 'initial' pour alimenter correctement les valeurs par défaut du formulaire
        form = PayslipCreateForm(initial={
            'month': default_month,
            'year': default_year,
            'working_days': 30,
            'absence_days': att_data['absence_days'],
            'daily_absence_rate': att_data['daily_absence_rate'],
            'paid_leave_days': getattr(employee, 'leave_balance', 0) or 0
        })

    return render(request, 'payroll/payslip_form.html', {'form': form, 'employee': employee})


@login_required
def payslip_recalculate(request, payslip_id):
    """Recalcule un bulletin existant en tenant compte des derniers congés et présences saisis"""
    payslip = get_object_or_404(Payslip, id=payslip_id, employee__company__owner=request.user)
    employee = payslip.employee
    company = employee.company

    # 1. Actualisation des absences et congés sans solde basés sur les dates
    att_data = calculate_attendance_deductions_for_month(employee, payslip.month, payslip.year)
    payslip.absence_days = att_data['absence_days']
    payslip.daily_absence_rate = att_data['daily_absence_rate']
    payslip.unpaid_absences_amount = att_data['unpaid_absences_amount']

    # 2. Recalcul global de la paie
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

    messages.success(request, f"Le bulletin de {employee.first_name} {employee.last_name} a été actualisé avec succès.")
    return redirect('payroll:payslip_detail', payslip_id=payslip.id)


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
            # Récupération automatique des absences et congés sans solde du mois pour chaque salarié
            att_data = calculate_attendance_deductions_for_month(employee, month, year)

            # Calcul avec les taux personnalisés de l'entreprise et les déductions automatiques
            calc = calculate_madagascar_payroll(
                base_salary=employee.base_salary,
                unpaid_absences=att_data['unpaid_absences_amount'],
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
                absence_days=att_data['absence_days'],
                paid_leave_days=0,
                daily_absence_rate=att_data['daily_absence_rate'],
                unpaid_absences_amount=att_data['unpaid_absences_amount'],
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

    # Tableau du PDF avec libellé unifié pour absences et congés sans solde
    data = [
        ["Désignation", "Gains (Ar)", "Retenues (Ar)"],
        ["Salaire de base", f"{payslip.employee.base_salary:,.2f}", "-"],
    ]

    if payslip.unpaid_absences_amount > 0:
        data.append(
            [f"Absences / Congés sans solde ({payslip.absence_days} j)", "-", f"{payslip.unpaid_absences_amount:,.2f}"])
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