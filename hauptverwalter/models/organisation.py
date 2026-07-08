from django.db import models
from hauptverwalter.models import dokumente
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

from .sitzungen import Legislatur


class Faden(models.Model):
    """Ein Faden. Repräsentiert einen Antrag, Bericht, Änderungsantrag etc, alles, was theoretisch Vertagt werden könnte,"""

    email = models.EmailField()
    kontaktperson = models.CharField(max_length=100)
    aktuelle_vorlage = models.ForeignKey(
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
            self.aktuelle_vorlage.titel
            if self.aktuelle_vorlage
            else "keine prf. Vorlage",
        )

    @property
    def vorlage(self):
        if self.aktuelle_vorlage:
            return self.aktuelle_vorlage
        else:
            return (
                dokumente.Vorlage.objects.filter(faden=self)
                .order_by("-eingereicht_organisatorisch")
                .first()
            )

    @property
    def aktenzeichen(self):
        if self.ueberfaden:
            nummer_in_ueberfaden = (
                Faden.objects.filter(ueberfaden=self.ueberfaden)
                .filter(id__lt=self.id)
                .count()
                + 1
            )
            return str(self.ueberfaden.aktenzeichen) + "." + str(nummer_in_ueberfaden)
        else:
            return (
                Faden.objects.filter(schiffchen__legislatur=self.schiffchen.legislatur)
                .filter(id__lt=self.id)
                .count()
                + 1
            )

    def clean(self, **kwargs):
        super().clean()
        if self.aktuelle_vorlage and not self.aktuelle_vorlage.faden == self:
            raise ValidationError(
                "Ausgewählte Aktuelle Vorlage gehört nicht zu diesem Faden!"
            )


class Schiffchen(models.Model):
    """Ein Schiffchen. In der Realität werden oft mehrere Fäden immer gemeinsam auf eine TO gesetzt (zb ein Antrag immer mit seinen Unteranträgen). Das Schiffchen repräsentiert diese Gruppierung von Fäden"""

    legislatur = models.ForeignKey(
        Legislatur,
        on_delete=models.CASCADE,
        related_name="schiffchen",
        null=True,
        blank=True,
    )
    hauptfaden = models.OneToOneField(
        # der Hauptfaden
        Faden,
        on_delete=models.CASCADE,
        related_name="schiffchen",
    )
    erwartete_lesungen = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Wie viele Lesungen werden für diesen Antrag erwartet? (1-10)",
    )

    @property
    def titel(self):
        pass

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

    schiffchen = models.ForeignKey(
        Schiffchen, on_delete=models.CASCADE, related_name="lesungen"
    )

    @property
    def nummer(self):
        """Die wievielte Lesung ist das (#Anzahl früherer Lesungen +1)"""
        return (
            Lesung.objects.filter(schiffchen=self.schiffchen)
            .filter(id__lt=self.id)
            .count()
            + 1
        )

    def __str__(self):
        return "Lesung {} für Antrag/Vorlage {}".format(
            self.nummer,
            self.schiffchen.hauptfaden.vorlage.titel
            if self.schiffchen.hauptfaden.vorlage
            else self.schiffchen.hauptfaden.aktenzeichen,
        )
