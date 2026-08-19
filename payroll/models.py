from django.db import models
from accounts.models import Company


class Employee(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    cin = models.CharField(max_length=50, verbose_name="N° CIN / Passeport")
    job_title = models.CharField(max_length=100, verbose_name="Fonction")
    contract_type = models.CharField(
        max_length=10,
        choices=[('CDD', 'CDD'), ('CDI', 'CDI')],
        default='CDD',
        verbose_name="Type de contrat"
    )
    hire_date = models.DateField(verbose_name="Date d'embauche")
    department = models.CharField(max_length=100, default='Général', verbose_name="Département")
    category = models.CharField(max_length=50, default='M1-1A', verbose_name="Catégorie Professionnelle")
    cnaps_no = models.CharField(max_length=50, default='0', verbose_name="N° CNaPS Salarié")
    children_count = models.IntegerField(default=0, verbose_name="Nombre d'enfants à charge")
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Salaire de Base (Ar)")

    # Solde de l'avance globale accordée au salarié
    total_advance_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                                verbose_name="Solde Avance globale en cours (Ar)")

    # Solde de congés payés restants (en jours)
    leave_balance = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                        verbose_name="Solde de congés restants (Jours)")

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    month = models.CharField(max_length=20, verbose_name="Mois de Paie")  # ex: "JUILLET"
    year = models.IntegerField(default=2026, verbose_name="Année")

    # Données variables de temps et d'absences
    working_days = models.IntegerField(default=30, verbose_name="Temps de travail (Jours)")
    absence_days = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                       verbose_name="Nombre de jours d'absence non payés")

    # Jours de congé payé pris pendant le mois
    paid_leave_days = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                          verbose_name="Nombre de jours de congé payé pris")

    daily_absence_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                             verbose_name="Retenue par jour d'absence (Ar)")
    unpaid_absences_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                                 verbose_name="Total Retenues Absences (Ar)")

    # Gains
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Heures supp. (h)")
    overtime_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                          verbose_name="Gains Heures supp. (Ar)")
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Primes et Indemnités (Ar)")

    # Déductions
    advances = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                   verbose_name="Retenue Avance sur salaire du mois (Ar)")

    # Résultats calculés (sauvegardés pour archivage)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Salaire Brut")
    cnaps_employee = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="CNaPS Salarié (1%)")
    smids_employee = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="SMIDS Salarié")
    taxable_base = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Base Imposable")
    irsa = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="IRSA")
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Net à Payer")

    # Cotisations Patronales
    cnaps_employer = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                         verbose_name="CNaPS Patronal (13%)")
    smids_employer = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                         verbose_name="SMIDS Patronal (5%)")
    fmfp_employer = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        verbose_name="FMFP Patronal (1%)")

    # Statut masqué/archivé du bulletin
    is_archived = models.BooleanField(default=False, verbose_name="Masqué/Archivé")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bulletin {self.month} {self.year} - {self.employee}"


# ==============================================================================
# Paramètres de paie configurables par chaque entreprise cliente (Uniquement en Taux)
# ==============================================================================
class PayrollSettings(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='payroll_settings')

    # Pourcentages modifiables par le client
    cnaps_employee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0100,
                                              verbose_name="Taux CNaPS Salarié")
    cnaps_employer_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.1300,
                                              verbose_name="Taux CNaPS Patronal")

    # AJOUT DU TAUX SMIDS SALARIÉ ICI
    smids_employee_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0100,
                                              verbose_name="Taux SMIDS Salarié")

    smids_employer_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0500,
                                              verbose_name="Taux SMIDS / OSTIE Patronal")
    fmfp_employer_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.0100,
                                             verbose_name="Taux FMFP Patronal")

    def __str__(self):
        return f"Paramètres de paie - {self.company.name}"


# ==============================================================================
# Suivi journalier des présences et absences
# ==============================================================================
class Attendance(models.Model):
    SHIFT_CHOICES = [
        ('morning', 'Matin (1/60)'),
        ('afternoon', 'Après-midi (1/60)'),
        ('night', 'Nuit (1/60)'),
        ('full_day', 'Journée complète (1/30)'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances', verbose_name="Salarié")
    date = models.DateField(verbose_name="Date")
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, verbose_name="Tranche / Période")
    is_excused = models.BooleanField(default=False, verbose_name="Congé / Absence autorisée (non déductible)")

    class Meta:
        unique_together = ('employee', 'date', 'shift')
        verbose_name = "Suivi de présence / absence"
        verbose_name_plural = "Suivis des présences et absences"

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.get_shift_display()})"


# ==============================================================================
# Gestion des Demandes et Suivi des Congés
# ==============================================================================
class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Validé'),
        ('rejected', 'Refusé')
    ]
    TYPE_CHOICES = [
        ('paid', 'Congé Payé'),
        ('unpaid', 'Sans Solde'),
        ('sick', 'Maladie')
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests', verbose_name="Salarié")
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    leave_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='paid', verbose_name="Type de congé")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Statut")
    reason = models.TextField(blank=True, null=True, verbose_name="Motif")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Demande de congé"
        verbose_name_plural = "Demandes de congés"

    def __str__(self):
        return f"{self.employee} : {self.get_leave_type_display()} du {self.start_date} au {self.end_date}"