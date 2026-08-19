from django import template
from payroll.models import Attendance

register = template.Library()

@register.filter(name='has_absence')
def has_absence(employee, arg_string):
    """
    Vérifie si un employé a une absence enregistrée pour une date et un shift donnés.
    Format attendu dans l'argument : "YYYY-MM-DD_shift" (ex: "2026-08-19_morning")
    """
    try:
        date_str, shift = arg_string.split('_', 1)
        return Attendance.objects.filter(employee=employee, date=date_str, shift=shift).exists()
    except Exception:
        return False

@register.filter(name='is_excused')
def is_excused(employee, arg_string):
    """
    Vérifie si l'absence est un congé / autorisée.
    """
    try:
        date_str, shift = arg_string.split('_', 1)
        att = Attendance.objects.filter(employee=employee, date=date_str, shift=shift).first()
        return att.is_excused if att else False
    except Exception:
        return False