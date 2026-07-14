from django.db import models
from scheduling.models import Timetable


class EvaluationBaseline(models.Model):
    """Manual timetabling baseline for comparison against the generated solution.

    Allows the evaluation chapter to quantify conflict reduction, time saved,
    and completeness improvement vs a hand-built timetable.
    """
    timetable = models.OneToOneField(
        Timetable, on_delete=models.CASCADE, related_name="baseline"
    )
    manual_conflicts = models.IntegerField(
        default=0,
        help_text="Hard constraint violations in the manually built timetable.",
    )
    manual_time_minutes = models.IntegerField(
        default=0,
        help_text="Estimated minutes to build the manual timetable.",
    )
    manual_sessions_scheduled = models.IntegerField(
        default=0,
        help_text="Sessions successfully placed in the manual timetable.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Evaluation Baseline"

    def __str__(self):
        return f"Baseline for {self.timetable}"

    @property
    def conflict_reduction(self):
        return self.manual_conflicts - self.timetable.hard_violations

    @property
    def conflict_reduction_pct(self):
        if self.manual_conflicts:
            return round(self.conflict_reduction / self.manual_conflicts * 100, 1)
        return None

    @property
    def session_delta(self):
        return self.timetable.scheduled_count - self.manual_sessions_scheduled

    @property
    def time_speedup_x(self):
        gen_ms = self.timetable.generation_time_ms
        if gen_ms and self.manual_time_minutes:
            return round(self.manual_time_minutes * 60_000 / gen_ms, 0)
        return None

    @property
    def time_saved_minutes(self):
        gen_min = self.timetable.generation_time_ms / 60_000
        return round(self.manual_time_minutes - gen_min, 1)
