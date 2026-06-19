from django.db import models

import uuid
from django.utils import timezone


class Vorlage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titel = models.CharField(max_length=255)
    text = models.TextField(max_length=20000)
    zeigen = models.BooleanField(
        default=True, help_text="Soll die Vorlage sichtbar sein?"
    )
    faden = models.ForeignKey(
        "hauptverwalter.Faden", on_delete=models.CASCADE, related_name="vorlagen"
    )
    eingereicht_technisch = models.DateTimeField(auto_now_add=True)
    eingereicht_organisatorisch = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return "Vorlage {}: {}".format(self.id, self.titel)


class Antrag(Vorlage):
    begruendung = models.TextField(max_length=40000)
    antragssteller = models.CharField(max_length=500)

    def __str__(self):
        return "Antrag {}: {} ({})".format(self.id, self.titel, self.antragssteller)


class Finanzantrag(Antrag):
    antragssumme = models.DecimalField(max_digits=20, decimal_places=2)
    haushaltsposten = models.CharField(
        max_length=10,
        help_text="Aus welchem Haushaltsposten wird Geld beantragt (nur Kennummer)?",
    )


class SOAntrag(Antrag):
    orgsatzungsaenderung = models.BooleanField(
        default=False,
        null=True,
        blank=True,
        help_text="Geht es um eine Änderung der Organisationssatzung?",
    )


class Anhang(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    datei = models.FileField(upload_to="anhang/")
    titel = models.CharField(max_length=255)
    hochgeladen_am = models.DateTimeField(auto_now_add=True)
    zeigen = models.BooleanField(
        default=True, help_text="Soll der Anhang sichtbar sein?"
    )
    faden = models.ForeignKey(
        "hauptverwalter.Faden", on_delete=models.CASCADE, related_name="anhaenge"
    )

    @property
    def nummer(self):
        # Nummeriere Anhänge pro Faden basierend auf dem Upload-Datum
        anhaenge_des_fadens = Anhang.objects.filter(faden=self.faden).order_by(
            "hochgeladen_am"
        )
        return list(anhaenge_des_fadens).index(self) + 1

    def __str__(self):
        return "Anhang {} für Faden {}".format(self.nummer, self.faden.id)
