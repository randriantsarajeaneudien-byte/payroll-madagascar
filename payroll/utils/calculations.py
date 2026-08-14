from decimal import Decimal, ROUND_HALF_UP


def round_currency(value):
    """Arrondit un montant au centième près (2 décimales)."""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_madagascar_payroll(base_salary, unpaid_absences=0, overtime=0, bonus=0, advance=0, children=0):
    base = Decimal(str(base_salary or 0))
    absences = Decimal(str(unpaid_absences or 0))
    overtime = Decimal(str(overtime or 0))
    bonus = Decimal(str(bonus or 0))
    advance = Decimal(str(advance or 0))

    # 1. Salaire Brut Total (Base - Absences + Heures Supp + Primes)
    gross_salary = (base - absences) + overtime + bonus
    if gross_salary < Decimal('0.00'):
        gross_salary = Decimal('0.00')

    # 2. Cotisations Salariales (CNaPS 1% plafonné selon 8 x SME + SMIDS 1%)
    # Plafond de base CNaPS (8 x SME = 8 x 262 680 Ar = 2 101 440 Ar)
    cnaps_max_base = Decimal('2101440.00')
    cnaps_taxable_base = min(gross_salary, cnaps_max_base)

    cnaps_employee = round_currency(cnaps_taxable_base * Decimal('0.01'))
    smids_employee = round_currency(gross_salary * Decimal('0.01'))  # 1% cotis. médicale salarié

    total_employee_deductions = cnaps_employee + smids_employee
    taxable_base = gross_salary - total_employee_deductions
    if taxable_base < Decimal('0.00'):
        taxable_base = Decimal('0.00')

    # 3. Calcul IRSA Madagascar (Minimum fixe de 3 000 Ar)
    if taxable_base <= Decimal('350000.00'):
        raw_irsa = Decimal('3000.00')
    else:
        taxable_amount = taxable_base - Decimal('350000.00')
        raw_irsa = Decimal('3000.00') + (taxable_amount * Decimal('0.20'))

    # Déduction pour enfants à charge (2 000 Ar par enfant à charge)
    child_deduction = Decimal(str(children or 0)) * Decimal('2000.00')
    irsa = max(Decimal('3000.00'), raw_irsa - child_deduction)
    irsa = round_currency(irsa)

    # 4. Net à Payer
    net_payable = gross_salary - total_employee_deductions - irsa - advance

    # 5. Cotisations Patronales
    cnaps_employer = round_currency(cnaps_taxable_base * Decimal('0.13'))  # CNaPS 13%
    smids_employer = round_currency(gross_salary * Decimal('0.05'))       # SMIDS/OSTIE 5%
    fmfp_employer = round_currency(gross_salary * Decimal('0.01'))        # FMFP 1%

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