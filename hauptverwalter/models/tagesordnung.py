from django.db import models
from .sitzungen import Sitzung
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class Tagesordnungspunkt(models.Model):
    ergebnis_choices = [
        ("E", "Erfolgreich behandelt"),
        ("X", "Manuell vertagt"),
        ("U", "Durch Sitzungsende vertagt"),
        ("A", "Abgestimmt/Entschieden"),
    ]
    lesung = models.ForeignKey(
        "Lesung",
        on_delete=models.CASCADE,
        related_name="tagesordnungspunkte",
        blank=True,
        null=True,
    )
    manueller_titel = models.CharField(max_length=100, blank=True, null=True)
    protokolltext = models.TextField(max_length=10000, blank=True, null=True)
    sitzung = models.ForeignKey(
        Sitzung, on_delete=models.CASCADE, related_name="tagesordnungspunkte"
    )
    nummer = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Die Nummer dieses TOPs in der Tagesordnung der Sitzung",
        null=True,
        blank=True,
    )
    ergebnis = models.CharField(
        choices=ergebnis_choices,
        max_length=1,
        blank=True,
        null=True,
    )
    dringlichkeit_beantragt = models.BooleanField(
        default=False,
    )

    @property
    def titel(self):
        return self.manueller_titel or self.lesung.__str__() or "Kein Titel"

    class Meta:
        unique_together = ["sitzung", "nummer"]

    def __str__(self):
        if self.nummer:
            return f"TOP {self.nummer} - {self.titel}"
        else:
            return f"Unnummerierter TOP - {self.titel}"

    def clean(self):
        # Nur Fäden ohne Überfaden dürfen Schiffchen haben
        if not self.lesung:
            if not self.manueller_titel:
                raise ValidationError(
                    "Tagesordnungspunkte, die keine Vorlage behandeln, brauchen einen manuellen Titel!"
                )


class Tischvorlage(Tagesordnungspunkt):
    begruendung = models.TextField(max_length=40000, blank=True, null=True)
    angenommen = models.BooleanField(default=False)
