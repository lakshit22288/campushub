from django import forms
from django.utils import timezone

from .models import (
    Announcement,
    AssignmentEntry,
    Book,
    Branch,
    CampusEvent,
    HelpRequest,
    HelpRequestReply,
    Note,
    Project,
    ScheduleEntry,
    Skill,
    SkillFeedback,
    SkillRequest,
    Subject,
    User,
)


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254)
    password = forms.CharField(strip=False, widget=forms.PasswordInput)


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(max_length=254)


class PasswordResetCompleteForm(forms.Form):
    access_token = forms.CharField(
        max_length=4096,
        strip=False,
        widget=forms.HiddenInput,
    )
    password = forms.CharField(
        min_length=6,
        max_length=72,
        strip=False,
        widget=forms.PasswordInput,
    )
    confirm_password = forms.CharField(
        min_length=6,
        max_length=72,
        strip=False,
        widget=forms.PasswordInput,
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("confirm_password")
        if password and confirmation and password != confirmation:
            self.add_error("confirm_password", "The passwords do not match.")
        if password and len(password.encode("utf-8")) > 72:
            self.add_error(
                "password",
                "The password cannot exceed 72 bytes when encoded as UTF-8.",
            )
        return cleaned_data


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(min_length=6, max_length=72, strip=False, widget=forms.PasswordInput)
    branch = forms.ModelChoiceField(queryset=Branch.objects.all(), required=False)
    semester = forms.IntegerField(min_value=1, max_value=12, required=False)


class GoogleProfileForm(forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.all())
    semester = forms.IntegerField(min_value=1, max_value=12, required=False)


class BookListingForm(forms.ModelForm):
    title = forms.CharField(
        max_length=160,
        widget=forms.TextInput(attrs={"maxlength": 160}),
    )
    author = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={"maxlength": 120}),
    )
    subject = forms.CharField(
        required=False,
        max_length=120,
        widget=forms.TextInput(attrs={"maxlength": 120}),
    )
    location = forms.CharField(
        required=False,
        max_length=160,
        widget=forms.TextInput(attrs={"maxlength": 160}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["available_until"].widget.attrs["min"] = timezone.localdate().isoformat()

    class Meta:
        model = Book
        fields = ("title", "author", "subject", "branch", "action", "location", "available_until")
        help_texts = {
            "available_until": "Optional. Leave blank if this listing has no end date.",
        }
        widgets = {
            "available_until": forms.DateInput(attrs={"type": "date"}),
            "title": forms.TextInput(attrs={"maxlength": 160}),
            "author": forms.TextInput(attrs={"maxlength": 120}),
            "subject": forms.TextInput(attrs={"maxlength": 120}),
            "location": forms.TextInput(attrs={"maxlength": 160}),
        }

    def clean_available_until(self):
        available_until = self.cleaned_data.get("available_until")
        if available_until and available_until < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return available_until


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ("skill_name", "type", "level")
        widgets = {"skill_name": forms.TextInput(attrs={"maxlength": 80})}


class SkillRequestForm(forms.Form):
    offered_skill = forms.ModelChoiceField(queryset=Skill.objects.none(), required=False)
    message = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
    )

    def __init__(self, *args, requester_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offered_skill"].queryset = Skill.objects.filter(
            user_id=requester_id, type="teach"
        ).order_by("skill_name")


class ProfileForm(forms.ModelForm):
    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if user.role == "super_admin":
            self.fields.pop("branch")
            self.fields.pop("semester")

    class Meta:
        model = User
        fields = ("name", "branch", "semester", "bio")
        widgets = {
            "name": forms.TextInput(attrs={"maxlength": 120}),
            "semester": forms.NumberInput(attrs={"min": 1, "max": 12}),
            "bio": forms.Textarea(attrs={"rows": 4, "maxlength": 500}),
        }


class HelpRequestForm(forms.ModelForm):
    class Meta:
        model = HelpRequest
        fields = ("title", "description", "branch")
        widgets = {
            "title": forms.TextInput(attrs={"maxlength": 160}),
            "description": forms.Textarea(attrs={"rows": 5, "maxlength": 3000}),
        }


class HelpRequestReplyForm(forms.ModelForm):
    message = forms.CharField(
        max_length=3000,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": 3000}),
        label="Your reply",
    )

    class Meta:
        model = HelpRequestReply
        fields = ("message",)


class ProjectForm(forms.Form):
    title = forms.CharField(max_length=160)
    description = forms.CharField(
        max_length=3000,
        widget=forms.Textarea(attrs={"rows": 5, "maxlength": 3000}),
    )
    difficulty = forms.ChoiceField(
        choices=(("beginner", "Beginner"), ("intermediate", "Intermediate"), ("advanced", "Advanced"))
    )
    required_skills = forms.CharField(
        max_length=500,
        required=False,
        help_text="Separate skills with commas.",
    )
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        required=True,
        empty_label="Choose one branch",
        label="Project branch",
        help_text="Each project can be listed under one branch.",
    )
    attachment = forms.FileField(
        required=False,
        label="Project file (optional)",
        help_text="Upload a ZIP, PDF, PNG or JPG project file (max 10 MB).",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": (
                    ".zip,.pdf,.png,.jpg,.jpeg,"
                    "application/zip,application/pdf,image/png,image/jpeg"
                )
            }
        ),
    )


class SkillFeedbackForm(forms.ModelForm):
    rating = forms.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = SkillFeedback
        fields = ("rating", "comment")
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "comment": forms.Textarea(attrs={"rows": 2, "maxlength": 500}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ("name", "branch")


class NoteForm(forms.Form):
    SOURCE_CHOICES = (
        (Note.SOURCE_TEACHER, "Teacher / faculty upload"),
        (Note.SOURCE_AI, "AI-generated study material"),
    )

    def __init__(self, *args, user_role=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user_role == "teacher":
            self.fields["source_type"].choices = self.SOURCE_CHOICES[:1]

    title = forms.CharField(max_length=160)
    description = forms.CharField(
        required=False,
        max_length=3000,
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 3000}),
    )
    upload_id = forms.CharField(required=False, widget=forms.HiddenInput)
    subject = forms.ModelChoiceField(queryset=Subject.objects.select_related("branch"))
    source_type = forms.ChoiceField(
        choices=SOURCE_CHOICES,
        initial=Note.SOURCE_TEACHER,
        label="Resource type",
    )
    file = forms.FileField(required=False)


class AnnouncementForm(forms.ModelForm):
    upload_id = forms.CharField(required=False, widget=forms.HiddenInput)
    attachment = forms.FileField(
        required=False,
        label="Notice image or PDF",
        help_text="Optional. Upload a PDF, PNG or JPG file (max 10 MB).",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"}
        ),
    )

    def __init__(self, *args, user_role=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user_role == "teacher":
            self.fields.pop("attachment")

    class Meta:
        model = Announcement
        fields = ("title", "message", "target_branch")
        widgets = {"message": forms.Textarea(attrs={"rows": 3, "maxlength": 3000})}


class CampusEventForm(forms.ModelForm):
    starts_at = forms.DateTimeField(
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    ends_at = forms.DateTimeField(
        input_formats=("%Y-%m-%dT%H:%M",),
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )

    class Meta:
        model = CampusEvent
        fields = ("title", "description", "location", "starts_at", "ends_at", "target_branch")
        widgets = {
            "title": forms.TextInput(attrs={"maxlength": 160}),
            "description": forms.Textarea(attrs={"rows": 4, "maxlength": 3000}),
            "location": forms.TextInput(attrs={"maxlength": 160}),
        }

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "The event end must be after its start.")
        return cleaned_data


class ScheduleEntryForm(forms.ModelForm):
    class Meta:
        model = ScheduleEntry
        fields = ("course", "day_of_week", "start_time", "end_time", "location")
        widgets = {
            "course": forms.TextInput(attrs={"maxlength": 120}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "location": forms.TextInput(attrs={"maxlength": 160}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "The class end time must be after its start time.")
        return cleaned_data


class AssignmentEntryForm(forms.ModelForm):
    class Meta:
        model = AssignmentEntry
        fields = ("title", "subject", "due_date", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"maxlength": 160}),
            "subject": forms.TextInput(attrs={"maxlength": 120}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "maxlength": 2000}),
        }
