from django import forms
from rest_framework.exceptions import ValidationError

from .images import clean_group_cover
from .models import EditorialGroup


class EditorialGroupForm(forms.ModelForm):
    class Meta:
        model = EditorialGroup
        fields = "__all__"
        help_texts = {"custom_cover": "JPG, PNG ou WebP, até 5 MB. Recomendado: 1600 × 900 px. Mínimo: 800 × 450 px. Máximo: 4096 × 4096 px. Recorte central em 16:9."}

    def clean_custom_cover(self):
        image = self.cleaned_data.get("custom_cover")
        if image and "custom_cover" in self.changed_data:
            try:
                return clean_group_cover(image)
            except ValidationError as error:
                raise forms.ValidationError(error.detail)
        return image

    def clean(self):
        data = super().clean()
        if data.get("custom_cover") and not data.get("cover_alt", "").strip():
            self.add_error("cover_alt", "Descreva a foto própria para quem usa leitor de tela.")
        return data
