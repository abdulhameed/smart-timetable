from django import forms
from .models import Department, AcademicSession, Period


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code"]


class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ["name", "semester", "is_active"]


class PeriodForm(forms.ModelForm):
    class Meta:
        model = Period
        fields = ["index", "label", "start_time", "end_time"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
