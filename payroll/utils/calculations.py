from decimal import Decimal, ROUND_HALF_UP
from accounts.models import IRSASetting
from payroll.models import Attendance, LeaveRequest


def round_currency(value):
    """Arrondit un montant au centième près (2 décimales)."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_attendance_deductions_for_month(employee, month_name, year):
    """
    Parcourt les présences/absences et congés sans solde enregistrés pour un employé sur un mois,
    calcule le nombre de jours d'absence non payés (en tenant compte des journées entières, demi-journées,
    ainsi que des périodes de congés sans solde) et calcule la retenue financière correspondante.
    """
    from datetime import date, timedelta

    # Dictionnaire de correspondance des mois textuels en numéro
    months_map = {
        "Janvier": 1, "Février": 2, "Mars": 3, "Avril": 4, "Mai": 5, "Juin": 6,
        "Juillet": 7, "Août": 8, "Septembre": 9, "Octobre": 10, "Novembre": 11, "Décembre": 12,
        "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
        "juillet": 7, "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
    }

    month_num = months_map.get(str(month_name).strip(), 1)
    y_int = int(year)

    # Détermination du premier et dernier jour du mois pour le calcul des congés
    debut_mois = date(y_int, month_num, 1)
    if month_num == 12:
        fin_mois = date(y_int + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mois = date(y_int, month_num + 1, 1) - timedelta(days=1)

    total_absence_days = Decimal('0.00')

    # 1. Traitement des absences ponctuelles (Attendance)
    attendances = Attendance.objects.filter(
        employee=employee,
        date__year=y_int,
        date__month=month_num,
        is_excused=False
    )

    for att in attendances:
        if att.shift in ['morning', 'afternoon', 'night']:
            total_absence_days += Decimal('0.50')  # Demi-journée
        elif att.shift == 'full_day':
            total_absence_days += Decimal('1.00')  # Journée complète

    # 2. Traitement des congés sans solde (LeaveRequest de type 'unpaid')
    unpaid_leaves = LeaveRequest.objects.filter(
        employee=employee,
        leave_type='unpaid',
        status='approved',
        start_date__lte=fin_mois,
        end_date__gte=debut_mois
    )

    for leave in unpaid_leaves:
        # Intersection entre la période de congé et le mois en cours
        d_debut = max(leave.start_date, debut_mois)
        d_fin = min(leave.end_date, fin_mois)
        nb_jours_conge = (d_fin - d_debut).days + 1
        if nb_jours_conge > 0:
            total_absence_days += Decimal(str(nb_jours_conge))

    # Calcul du taux journalier (Salaire de base / 30)
    base_salary = employee.base_salary
    daily_rate = base_salary / Decimal('30')

    # Montant total de la retenue pour absence et congés sans solde (Taux journalier * Nombre de jours d'absence)
    unpaid_amount = round_currency(daily_rate * total_absence_days)

    return {
        'absence_days': total_absence_days.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'unpaid_absences_amount': unpaid_amount,
        'daily_absence_rate': round_currency(daily_rate)
    }


def calculate_madagascar_payroll(base_salary, unpaid_absences=0, overtime=0, bonus=0, advance=0, children=0, company=None):
    base = Decimal(str(base_salary or 0))
    absences = Decimal(str(unpaid_absences or 0))
    overtime = Decimal(str(overtime or 0))
    bonus = Decimal(str(bonus or 0))
    advance = Decimal(str(advance or 0))

    # Récupération des taux personnalisés de l'entreprise (ou valeurs par défaut de secours)
    if company and hasattr(company, 'payroll_settings'):
        settings = company.payroll_settings
        r_cnaps_emp = settings.cnaps_employee_rate
        r_cnaps_empr = settings.cnaps_employer_rate
        r_smids_empr = settings.smids_employer_rate
        r_fmfp_empr = settings.fmfp_employer_rate
    else:
        r_cnaps_emp = Decimal('0.0100')
        r_cnaps_empr = Decimal('0.1300')
        r_smids_empr = Decimal('0.0500')
        r_fmfp_empr = Decimal('0.0100')

    # 1. Salaire Brut Total (Base - Absences et Congés sans solde + Heures Supp + Primes)
    gross_salary = (base - absences) + overtime + bonus
    if gross_salary < Decimal('0.00'):
        gross_salary = Decimal('0.00')

    # 2. Cotisations Salariales
    cnaps_max_base = Decimal('2101440.00')
    cnaps_taxable_base = min(gross_salary, cnaps_max_base)

    cnaps_employee = round_currency(cnaps_taxable_base * r_cnaps_emp)
    smids_employee = round_currency(gross_salary * r_cnaps_emp)

    total_employee_deductions = cnaps_employee + smids_employee
    taxable_base = gross_salary - total_employee_deductions
    if taxable_base < Decimal('0.00'):
        taxable_base = Decimal('0.00')

    # Récupération de la configuration IRSA
    irsa_config = IRSASetting.objects.first()
    if irsa_config:
        min_irsa = irsa_config.minimum_irsa
        child_deduction_amount = irsa_config.child_deduction_amount
        t1 = irsa_config.tranche_1_limit
        t2 = irsa_config.tranche_2_limit
        t3 = irsa_config.tranche_3_limit
        t4 = irsa_config.tranche_4_limit
        t5 = irsa_config.tranche_5_limit
    else:
        min_irsa = Decimal('3000.00')
        child_deduction_amount = Decimal('2000.00')
        t1 = Decimal('350000.00')
        t2 = Decimal('400000.00')
        t3 = Decimal('500000.00')
        t4 = Decimal('600000.00')
        t5 = Decimal('4000000.00')

    # 3. Calcul IRSA Madagascar par tranches progressives dynamiques
    raw_irsa = Decimal('0.00')
    temp_taxable_base = taxable_base

    if temp_taxable_base > t5:
        raw_irsa += (temp_taxable_base - t5) * Decimal('0.25')
        temp_taxable_base = t5
    if temp_taxable_base > t4:
        raw_irsa += (temp_taxable_base - t4) * Decimal('0.20')
        temp_taxable_base = t4
    if temp_taxable_base > t3:
        raw_irsa += (temp_taxable_base - t3) * Decimal('0.15')
        temp_taxable_base = t3
    if temp_taxable_base > t2:
        raw_irsa += (temp_taxable_base - t2) * Decimal('0.10')
        temp_taxable_base = t2
    if temp_taxable_base > t1:
        raw_irsa += (temp_taxable_base - t1) * Decimal('0.05')

    child_deduction = Decimal(str(children or 0)) * child_deduction_amount
    irsa_after_deduction = raw_irsa - child_deduction

    if gross_salary > t1:
        irsa = max(min_irsa, irsa_after_deduction)
    else:
        irsa = Decimal('0.00')

    irsa = round_currency(irsa)

    # 4. Net à Payer
    net_payable = gross_salary - total_employee_deductions - irsa - advance

    # 5. Cotisations Patronales
    cnaps_employer = round_currency(cnaps_taxable_base * r_cnaps_empr)
    smids_employer = round_currency(gross_salary * r_smids_empr)
    fmfp_employer = round_currency(gross_salary * r_fmfp_empr)

    return {
        'gross_salary': round_currency(gross_salary),
        'cnaps_employee': cnaps_employee,
        'smids_employee': smids_employee,
        'taxable_base': round_currency(taxable_base),
        'irsa': irsa,
        'net_payable': round_currency(net_payable),
        'cnaps_employer': cnaps_employer,
        'smids_employer': smids_employer,
        'fmfp_employer': fmfp_employer,
    }