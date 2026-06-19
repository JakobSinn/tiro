from django.db import models
from hauptverwalter.models import dokumente
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid

from .sitzungen import Legislatur


class Faden(models.Model):
    """Ein Faden. Repräsäntiert einen Antrag, Bericht, Änderungsantrag etc, alles, was theoretisch Vertagt werden könnte,"""

    id = models.AutoField(primary_key=True)
    email = models.EmailField()
    kontaktperson = models.CharField(max_length=100)
    aktuelle_vl = models.ForeignKey(
        dokumente.Vorlage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faden_aktuell",
    )
    ueberfaden = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="unterfaeden",
    )

    def __str__(self):
        return "Faden {} ({})".format(
            self.id,
            self.aktuelle_vl.titel if self.aktuelle_vl else "keine prf. Vorlage",
        )

    @property
    def vorlage(self):
        if self.aktuelle_vl:
            return self.aktuelle_vl
        return (
            dokumente.Vorlage.objects.filter(faden=self)
            .order_by("-eingereicht_organisatorisch")
            .first()
        )


class Schiffchen(models.Model):
    """Ein Schiffchen. In der Realität werden oft mehrere Fäden immer gemeinsam auf eine TO gesetzt (zb ein Antrag immer mit seinen Unteranträgen). Das Schiffchen repräsentiert diese Gruppierung von Fäden"""

    id = models.AutoField(primary_key=True)
    legislatur = models.ForeignKey(
        Legislatur,
        on_delete=models.CASCADE,
        related_name="schiffchen",
        null=True,
        blank=True,
    )
    hauptfaden = models.ForeignKey(
        # der Hauptfaden
        Faden,
        on_delete=models.CASCADE,
        related_name="schiffchen",
    )
    erwartete_lesungen = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Wie viele Lesungen werden für diesen Antrag erwartet? (1-10)",
    )

    def __str__(self):
        return "Schiffchen {} ({})".format(
            self.id,
            self.hauptfaden.vorlage.titel
            if self.hauptfaden.vorlage
            else "keine Vorlage",
        )

    def clean(self):
        # Nur Fäden ohne Überfaden dürfen Schiffchen haben
        if self.hauptfaden.ueberfaden is not None:
            raise ValidationError(
                "Schiffchen dürfen nur an Fäden ohne Überfaden angehängt werden."
            )


class Lesung(models.Model):
    """Eine Lesung."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schiffchen = models.ForeignKey(
        Schiffchen, on_delete=models.CASCADE, related_name="lesungen"
    )
    dringlichkeit_beantragt = models.BooleanField(
        default=False,
        help_text="Könnte in dieser Lesung abgestimmt werden, wenn ein Dringlichkeitsantrag angenommen wird?",
    )

    @property
    def nummer(self):
        pass

    @property
    def planmaessig_abstimmbar(self):
        pass

    def __str__(self):
        return "Lesung {} für Antrag {}".format(
            self.nummer,
            self.schiffchen.vorlage.titel
            if self.schiffchen.vorlage
            else "keine Vorlage",
        )
