from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


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
    nummer = models.AutoField(primary_key=True, validators=[MinValueValidator(1)])
    anfang = models.DateTimeField()
    ende = models.DateTimeField(null=True, blank=True)
    legislatur = models.ForeignKey(
        Legislatur, on_delete=models.CASCADE, related_name="sitzungen"
    )
    ort = models.CharField(max_length=255)


class Sondersitzung(Sitzung):
    anmerkung = models.CharField(max_length=1000, blank=True, null=True)
