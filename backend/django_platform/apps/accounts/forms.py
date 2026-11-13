from uuid import uuid4

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import UserChangeForm, UserCreationForm


class UniqueEmailMixin:
    email = forms.EmailField(label="E-mail", max_length=254)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing = get_user_model().objects.filter(email__iexact=email)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email


class AccountCreationForm(UniqueEmailMixin, UserCreationForm):
    email = forms.EmailField(label="E-mail", max_length=254)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ["email", "first_name", "last_name"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = uuid4().hex
        if commit:
            user.save()
            self.save_m2m()
        return user


class AccountChangeForm(UniqueEmailMixin, UserChangeForm):
    email = forms.EmailField(label="E-mail", max_length=254)


class EmailAdminAuthenticationForm(AdminAuthenticationForm):
    username = forms.EmailField(label="E-mail", widget=forms.EmailInput(attrs={"autofocus": True}))
