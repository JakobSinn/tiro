from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from datetime import date


def _as_date(value):
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value


class Legislatur(models.Model):
    nummer = models.IntegerField(
        primary_key=True,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
    )
    anfang = models.DateField()
    ende = models.DateField()

    def __str__(self):
        return "{}. Legislaturperiode".format(self.nummer)


class Sitzung(models.Model):
    nummer = models.IntegerField(primary_key=True, validators=[MinValueValidator(1)])
    anfang = models.DateTimeField()
    ende = models.DateTimeField(null=True, blank=True)
    legislatur = models.ForeignKey(
        Legislatur, on_delete=models.CASCADE, related_name="sitzungen"
    )
    ort = models.CharField(max_length=255)
    anmerkungen = models.CharField(max_length=200, blank=True, null=True)
    protokoll_beschlossen_in = models.ForeignKey(
        "Sitzung",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="beschlossene_protokolle",
    )

    @property
    def is_past(self):
        if self.ende is not None:
            return True
        else:
            return False

    def clean(self):
        super().clean()
        if self.legislatur and self.anfang:
            start_datum = self.anfang.date()
            legislatur_anfang = _as_date(self.legislatur.anfang)
            legislatur_ende = _as_date(self.legislatur.ende)
            if start_datum < legislatur_anfang or start_datum > legislatur_ende:
                raise ValidationError(
                    {"anfang": "Die Sitzung muss innerhalb der Legislatur beginnen."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Sondersitzung(Sitzung):
    anmerkung = models.CharField(max_length=1000, blank=True, null=True)
