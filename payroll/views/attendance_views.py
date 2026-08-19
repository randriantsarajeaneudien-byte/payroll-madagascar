from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from accounts.models import Company
from ..models import Employee, Attendance
from ..utils.pdf_generator import generate_attendance_pdf_response


@login_required
def attendance_dashboard(request):
    company = get_object_or_404(Company, owner=request.user)
    employees = Employee.objects.filter(company=company)

    # Date sélectionnée (par défaut aujourd'hui)
    date_str = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        current_date = timezone.now().date()
        date_str = current_date.strftime('%Y-%m-%d')

    if request.method == 'POST':
        for emp in employees:
            for shift_val, _ in Attendance.SHIFT_CHOICES:
                field_name = f"attendance_{emp.id}_{shift_val}"
                excused_field = f"excused_{emp.id}"

                is_checked = request.POST.get(field_name) == 'on'
                is_excused = request.POST.get(excused_field) == 'on'

                att, created = Attendance.objects.get_or_create(
                    employee=emp, date=current_date, shift=shift_val
                )

                if is_checked:
                    att.is_excused = is_excused
                    att.save()
                else:
                    att.delete()

        messages.success(request, f"Présences mises à jour pour le {date_str}.")
        return redirect(f"{request.path}?date={date_str}")

    # Récupération des enregistrements existants sous forme de chaînes "empId_shift"
    existing_records = Attendance.objects.filter(date=current_date, employee__in=employees)
    absence_keys = {f"{att.employee_id}_{att.shift}" for att in existing_records}

    context = {
        'employees': employees,
        'current_date': date_str,
        'shift_choices': Attendance.SHIFT_CHOICES,
        'absence_keys': absence_keys,  # Utilisé par le template HTML
    }
    return render(request, 'payroll/attendance.html', context)


@login_required
def export_attendance_pdf(request):
    """
    Vue pour exporter la fiche de présence au format PDF pour une date donnée.
    """
    company = get_object_or_404(Company, owner=request.user)
    date_str = request.GET.get('date', timezone.now().strftime('%Y-%m-%d'))

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        target_date = timezone.now().date()
        date_str = target_date.strftime('%Y-%m-%d')

    employees = Employee.objects.filter(company=company)

    # Construction des enregistrements pour le générateur PDF
    records = []
    for emp in employees:
        att_dict = {
            'employee': emp,
            'morning': Attendance.objects.filter(employee=emp, date=target_date, shift='morning').exists(),
            'afternoon': Attendance.objects.filter(employee=emp, date=target_date, shift='afternoon').exists(),
            'night': Attendance.objects.filter(employee=emp, date=target_date, shift='night').exists(),
            'full_day': Attendance.objects.filter(employee=emp, date=target_date, shift='full_day').exists(),
        }
        records.append(att_dict)

    return generate_attendance_pdf_response(company, date_str, records, request.user)