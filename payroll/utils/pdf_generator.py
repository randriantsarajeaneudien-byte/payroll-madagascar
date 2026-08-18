from io import BytesIO
import re
from urllib.parse import quote

from django.http import HttpResponse, HttpResponseForbidden
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from ..models import PayrollSettings  # <-- Import des paramètres de paie


def generate_payslip_pdf_response(payslip, request_user):
    """
    Génère le document PDF du bulletin de paie et retourne la réponse HTTP.
    """
    if payslip.employee.company.owner != request_user:
        return HttpResponseForbidden("Vous n'avez pas l'autorisation d'accéder à ce document.")

    # Récupération des taux personnalisés de l'entreprise (ou valeurs par défaut)
    company = payslip.employee.company
    settings, created = PayrollSettings.objects.get_or_create(company=company)

    # Conversion des taux décimaux (ex: 0.01 -> "1%", 0.13 -> "13%")
    cnaps_emp_rate_str = f"{int(settings.cnaps_employee_rate * 100)}%"
    cnaps_pat_rate_str = f"{int(settings.cnaps_employer_rate * 100)}%"
    smids_emp_rate_str = f"{int(settings.smids_employee_rate * 100)}%"
    smids_pat_rate_str = f"{int(settings.smids_employer_rate * 100)}%"
    fmfp_pat_rate_str = f"{int(settings.fmfp_employer_rate * 100)}%"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25,
        leftMargin=25,
        topMargin=20,
        bottomMargin=20
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.black
    )
    cell_style = ParagraphStyle('CellStyle', fontName='Helvetica', fontSize=8, leading=10)
    bold_style = ParagraphStyle('BoldStyle', fontName='Helvetica-Bold', fontSize=8, leading=10)
    right_style = ParagraphStyle('RightStyle', fontName='Helvetica', fontSize=8, leading=10, alignment=2)
    bold_right = ParagraphStyle('BoldRight', fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=2)

    # 1. Titre
    title_data = [[Paragraph("BULLETIN DE PAIE", title_style)]]
    title_table = Table(title_data, colWidths=[545])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EAEAEA")),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(title_table)
    story.append(Spacer(1, 8))

    # 2. Section Employeur
    emp_data = [
        [
            Paragraph(f"<b>{company.name}</b><br/>{company.address}", cell_style),
            Paragraph(
                f"<b>NIF :</b> {company.nif}<br/><b>STAT :</b> {getattr(company, 'stat', None) or '-'}<br/><b>CNaPS :</b> {company.cnaps_no}",
                cell_style)
        ]
    ]
    emp_table = Table(emp_data, colWidths=[272, 273])
    emp_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 6))

    # 3. Section Salarié
    e = payslip.employee
    hire_date_str = e.hire_date.strftime("%d/%m/%Y") if getattr(e, 'hire_date', None) else "-"

    paid_leave = getattr(payslip, 'paid_leave_days', 0) or 0
    leave_bal = getattr(e, 'leave_balance', 0) or 0
    time_info_str = f"{payslip.working_days} J. | Congés pris: {paid_leave} j (Solde: {leave_bal} j) | Abs. non payées: {payslip.absence_days} j"

    employee_data = [
        [Paragraph("PAYE MOIS", bold_style), Paragraph(f"{payslip.month} {payslip.year}", cell_style),
         Paragraph("DATE D'EMBAUCHE", bold_style), Paragraph(hire_date_str, cell_style)],
        [Paragraph("NOM & PRENOM", bold_style), Paragraph(f"{e.last_name} {e.first_name}", cell_style),
         Paragraph("DEPARTEMENT", bold_style), Paragraph(str(getattr(e, 'department', None) or '-'), cell_style)],
        [Paragraph("CIN", bold_style), Paragraph(str(getattr(e, 'cin', None) or '-'), cell_style),
         Paragraph("CATEGORIE", bold_style), Paragraph(str(getattr(e, 'category', None) or '-'), cell_style)],
        [Paragraph("FONCTION", bold_style), Paragraph(str(getattr(e, 'job_title', None) or '-'), cell_style),
         Paragraph("CNaPS SALARIÉ", bold_style), Paragraph(str(getattr(e, 'cnaps_no', None) or '-'), cell_style)],
        [Paragraph("CONTRAT", bold_style), Paragraph(str(getattr(e, 'contract_type', None) or '-'), cell_style),
         Paragraph("ENFANTS À CHARGE", bold_style), Paragraph(str(getattr(e, 'children_count', 0)), cell_style)],
        [Paragraph("SALAIRE DE BASE", bold_style), Paragraph(f"<b>{e.base_salary:,.2f} Ar</b>", cell_style),
         Paragraph("TEMPS & CONGÉS", bold_style), Paragraph(time_info_str, cell_style)],
    ]
    emp_info_table = Table(employee_data, colWidths=[110, 162, 120, 153])
    emp_info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(emp_info_table)
    story.append(Spacer(1, 8))

    # 4. Tableau Calculs de Paie (avec taux dynamiques injectés)
    absence_label = f"Absences ({payslip.absence_days} j × {payslip.daily_absence_rate:,.2f} Ar)" if payslip.absence_days > 0 else "Absences / Retenues"
    advance_label = f"Retenue Avance (Reste dû: {e.total_advance_balance:,.2f} Ar)" if e.total_advance_balance > 0 else "Avance sur salaire"

    calc_data = [
        [
            Paragraph("<b>DÉSIGNATION</b>", bold_style),
            Paragraph("<b>GAINS</b>", bold_right),
            Paragraph("<b>RETENUES</b>", bold_right),
            Paragraph("<b>TAUX PAT.</b>", bold_style),
            Paragraph("<b>MONTANT PAT.</b>", bold_right)
        ],
        [Paragraph("Salaire de Base", cell_style), Paragraph(f"{e.base_salary:,.2f}", right_style),
         Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph(absence_label, cell_style), Paragraph("", cell_style),
         Paragraph(f"{payslip.unpaid_absences_amount:,.2f}", right_style), Paragraph("", cell_style),
         Paragraph("", cell_style)],
        [Paragraph("Heures Supplémentaires", cell_style), Paragraph(f"{payslip.overtime_amount:,.2f}", right_style),
         Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph("Primes et Indemnités", cell_style), Paragraph(f"{payslip.bonuses:,.2f}", right_style),
         Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph("<b>TOTAL BRUT</b>", bold_style), Paragraph(f"<b>{payslip.gross_salary:,.2f}</b>", bold_right),
         Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph(f"CNaPS ({cnaps_emp_rate_str})", cell_style), Paragraph("", cell_style),
         Paragraph(f"{payslip.cnaps_employee:,.2f}", right_style), Paragraph(cnaps_pat_rate_str, cell_style),
         Paragraph(f"{payslip.cnaps_employer:,.2f}", right_style)],
        [Paragraph(f"SMIDS / OSTIE ({smids_emp_rate_str})", cell_style), Paragraph("", cell_style),
         Paragraph(f"{payslip.smids_employee:,.2f}", right_style), Paragraph(smids_pat_rate_str, cell_style),
         Paragraph(f"{payslip.smids_employer:,.2f}", right_style)],
        [Paragraph("FMFP", cell_style), Paragraph("", cell_style), Paragraph("", cell_style),
         Paragraph(fmfp_pat_rate_str, cell_style), Paragraph(f"{payslip.fmfp_employer:,.2f}", right_style)],
        [Paragraph("<b>BASE IMPOSABLE</b>", bold_style), Paragraph(f"<b>{payslip.taxable_base:,.2f}</b>", bold_right),
         Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph("<b>IRSA</b>", bold_style), Paragraph("", cell_style),
         Paragraph(f"<b>{payslip.irsa:,.2f}</b>", bold_right), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph(advance_label, cell_style), Paragraph("", cell_style),
         Paragraph(f"{payslip.advances:,.2f}", right_style), Paragraph("", cell_style), Paragraph("", cell_style)],
        [Paragraph("<b>NET À PAYER</b>", bold_style), Paragraph(f"<b>{payslip.net_payable:,.2f} Ar</b>", bold_right),
         Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)],
    ]

    calc_table = Table(calc_data, colWidths=[205, 85, 85, 70, 100])
    calc_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F0F0F0")),
        ('BACKGROUND', (0, 5), (1, 5), colors.HexColor("#F0F0F0")),
        ('BACKGROUND', (0, 9), (1, 9), colors.HexColor("#F0F0F0")),
        ('BACKGROUND', (0, 12), (1, 12), colors.HexColor("#EAEAEA")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(calc_table)
    story.append(Spacer(1, 15))

    # 5. Signatures
    sig_data = [
        [Paragraph("<b><u>L'EMPLOYEUR</u></b>", bold_style), Paragraph("<b><u>LE SALARIÉ</u></b>", bold_style)]
    ]
    sig_table = Table(sig_data, colWidths=[272, 273])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
    ]))
    story.append(sig_table)

    doc.build(story)

    pdf_data = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_data, content_type='application/pdf')

    last_name = re.sub(r'[^\w\s-]', '', e.last_name).strip().replace(' ', '_')
    first_name = re.sub(r'[^\w\s-]', '', e.first_name).strip().replace(' ', '_')
    month = re.sub(r'[^\w\s-]', '', str(payslip.month)).strip().replace(' ', '_')
    year = str(payslip.year)

    filename = f"Bulletin_{last_name}_{first_name}_{month}_{year}.pdf"
    encoded_filename = quote(filename)

    response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
    return response