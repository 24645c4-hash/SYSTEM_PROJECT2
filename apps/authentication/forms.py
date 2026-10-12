"""Forms used for secure staff account management."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group

from .models import DoctorProfile, StaffProfile
from .roles import ADMIN, DOCTOR, RECEPTIONIST, ROLE_NAMES

User = get_user_model()


class MediManagePasswordChangeForm(PasswordChangeForm):
    """Require only a new password, which is clearer for first-login setup."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields.pop("old_password", None)


class StaffAccountCreationForm(forms.Form):
    """Create a clinic staff user and attach their role profile."""

    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150, required=False, label="First name")
    last_name = forms.CharField(max_length=150, required=False, label="Last name")
    email = forms.EmailField(required=False)
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")
    role = forms.ChoiceField(choices=((ADMIN, "Administrator"), (RECEPTIONIST, "Receptionist"), (DOCTOR, "Doctor")))

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not username:
            raise forms.ValidationError("Username is required.")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields did not match.")

        role = cleaned_data.get("role")
        if role and role.upper() not in ROLE_NAMES:
            raise forms.ValidationError("Choose a valid clinic role.")
        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data["username"].strip(),
            first_name=self.cleaned_data.get("first_name", "").strip(),
            last_name=self.cleaned_data.get("last_name", "").strip(),
            email=self.cleaned_data.get("email", ""),
            password=self.cleaned_data["password1"],
            is_staff=True,
        )
        role = self.cleaned_data["role"].upper()
        role_group = Group.objects.get_or_create(name=role)[0]
        user.groups.add(role_group)

        staff_profile = StaffProfile.objects.create(
            user=user,
            role=role,
            department="",
        )
        if role == DOCTOR:
            DoctorProfile.objects.get_or_create(staff_profile=staff_profile)
        if commit:
            user.save()
        return user, staff_profile
