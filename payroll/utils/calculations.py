from decimal import Decimal, ROUND_HALF_UP
from accounts.models import IRSASetting


def round_currency(value):
    """Arrondit un montant au centième près (2 décimales)."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


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
        # Valeurs par défaut si aucun paramètre n'est trouvé
        r_cnaps_emp = Decimal('0.0100')
        r_cnaps_empr = Decimal('0.1300')
        r_smids_empr = Decimal('0.0500')
        r_fmfp_empr = Decimal('0.0100')

    # 1. Salaire Brut Total (Base - Absences + Heures Supp + Primes)
    gross_salary = (base - absences) + overtime + bonus
    if gross_salary < Decimal('0.00'):
        gross_salary = Decimal('0.00')

    # 2. Cotisations Salariales (CNaPS et SMIDS basés sur les taux de l'entreprise)
    cnaps_max_base = Decimal('2101440.00')  # Plafond légal éventuel
    cnaps_taxable_base = min(gross_salary, cnaps_max_base)

    cnaps_employee = round_currency(cnaps_taxable_base * r_cnaps_emp)
    smids_employee = round_currency(gross_salary * r_cnaps_emp)  # Utilise le taux salarial configuré

    total_employee_deductions = cnaps_employee + smids_employee
    taxable_base = gross_salary - total_employee_deductions
    if taxable_base < Decimal('0.00'):
        taxable_base = Decimal('0.00')

    # Récupération de la configuration IRSA depuis l'Admin Django (singleton)
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
        # Valeurs de secours par défaut
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

    # Déduction pour enfants à charge
    child_deduction = Decimal(str(children or 0)) * child_deduction_amount

    # Application de la réduction pour charges de famille
    irsa_after_deduction = raw_irsa - child_deduction

    # Minimum de perception légal si le brut imposable dépasse la première limite
    if gross_salary > t1:
        irsa = max(min_irsa, irsa_after_deduction)
    else:
        irsa = Decimal('0.00')

    irsa = round_currency(irsa)

    # 4. Net à Payer
    net_payable = gross_salary - total_employee_deductions - irsa - advance

    # 5. Cotisations Patronales (Basées sur les taux de l'entreprise)
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