from django.db import models
from .sitzungen import Sitzung
from django.core.validators import MinValueValidator


class Tagesordnungspunkt(models.Model):
    ergebnis_choices = [
        ("E", "Erfolgreich behandelt"),
        ("X", "Manuell vertagt"),
        ("U", "Durch Sitzungsende vertagt"),
        ("A", "Abgestimmt/Entschieden"),
    ]
    id = models.AutoField(primary_key=True)
    lesung = models.ForeignKey(
        "Lesung", on_delete=models.CASCADE, related_name="tagesordnungspunkte"
    )
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

    class Meta:
        unique_together = ["sitzung", "nummer"]

    def __str__(self):
        if self.nummer:
            return f"TOP {self.nummer} - {self.lesung.schiffchen.id}"
        else:
            return f"Unnummerierter TOP - {self.lesung.schiffchen.id}"


class Tischvorlage(Tagesordnungspunkt):
    begruendung = models.TextField(max_length=40000, blank=True, null=True)
    angenommen = models.BooleanField(default=False)
