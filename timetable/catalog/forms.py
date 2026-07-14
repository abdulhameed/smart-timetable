from django import forms
from .models import Venue, Lecturer, Course, CourseLecturer


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "capacity", "venue_type", "location"]


class LecturerForm(forms.ModelForm):
    class Meta:
        model = Lecturer
        fields = ["name", "email", "department"]


class CourseForm(forms.ModelForm):
    lecturers = forms.ModelMultipleChoiceField(
        queryset=Lecturer.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Assign lecturers to this course.",
    )

    class Meta:
        model = Course
        fields = [
            "code", "title", "credit_units", "department",
            "class_size", "weekly_sessions", "session_length",
            "required_venue_type", "academic_session",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lecturers"].queryset = Lecturer.objects.select_related("department")
        if self.instance.pk:
            self.fields["lecturers"].initial = self.instance.lecturers.all()

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            CourseLecturer.objects.filter(course=instance).delete()
            for lecturer in self.cleaned_data.get("lecturers", []):
                CourseLecturer.objects.create(course=instance, lecturer=lecturer)
        return instance
