from django import forms
from .models import Antrag


class BaseAntragForm(forms.ModelForm):
    class Meta:
        model = Antrag
        fields = [
            "text",
            "begruendung",
            "antragssteller",
            "kontaktperson",
            "kontaktemail",
            "anhang",
        ]
        labels = {
            "text": "Zu beschliessender Antragstext",
        }
