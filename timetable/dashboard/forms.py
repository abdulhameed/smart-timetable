from django import forms
from .models import EvaluationBaseline


class EvaluationBaselineForm(forms.ModelForm):
    class Meta:
        model = EvaluationBaseline
        fields = ["manual_conflicts", "manual_time_minutes", "manual_sessions_scheduled", "notes"]
        labels = {
            "manual_conflicts": "Manual conflicts (hard violations)",
            "manual_time_minutes": "Manual construction time (minutes)",
            "manual_sessions_scheduled": "Sessions placed manually",
            "notes": "Notes / observations",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
