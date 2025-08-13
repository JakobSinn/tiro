from django.db import models, transaction
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
import uuid
import os


# Eine StuRa-Legislaturperiode. Ihr werden Anträge und Sitzungen zugeordnet
class Legislatur(models.Model):
    nummer = models.IntegerField(
        primary_key=True,
        help_text="Nummer Legislaturperiode",
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
    )
    anfangsdatum = models.DateField(
        help_text="Wann beginnt die Legislaturperiode?",
    )
    enddatum = models.DateField(
        help_text="Wann endet die Legislaturperiode?",
    )

    def __str__(self):
        return "Legislaturperiode " + str(self.nummer)


class Sitzung(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legislatur = models.ForeignKey(
        "Legislatur",
        on_delete=models.CASCADE,
        editable=False,
    )
    nummer = models.IntegerField(
        help_text="Nummer der Sitzung",
        editable=False,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        null=True,
    )
    anfang = models.DateTimeField(
        help_text="Wann beginnt die Sitzung?",
    )
    ende = models.DateTimeField(
        help_text="Wann endete die Sitzung?",
        blank=True,
        null=True,
    )
    sondersitzung = models.BooleanField(
        blank=True,
        help_text="Ist die Sitzung eine Sondersitzung?",
    )
    anmerkungen = models.TextField(
        blank=True,
        null=True,
        max_length=1000,
    )
    ort = models.CharField(
        max_length=1000,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["legislatur", "nummer"],
                name="unique_legislatur_nummer_sitzung",
            )
        ]

        ordering = ["-legislatur__nummer", "-nummer"]

    def clean(self):
        """Custom validation for Sitzung."""
        if self.legislatur_id and self.anfang:
            if not (
                self.legislatur.anfangsdatum
                <= self.anfang.date()
                <= self.legislatur.enddatum
            ):
                raise ValidationError(
                    {
                        "anfang": f"Das Datum {self.anfang.date()} liegt nicht innerhalb "
                        f"der Legislaturperiode {self.legislatur.anfangsdatum} bis {self.legislatur.enddatum}."
                    }
                )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # If no legislatur is set, pick the latest one
            if self.legislatur_id is None:
                latest_legislatur = Legislatur.objects.order_by("-nummer").first()
                if latest_legislatur is None:
                    raise ValueError("No Legislatur exists to assign to Sitzung.")
                self.legislatur = latest_legislatur

            # Auto-assign nummer if missing
            if self.nummer is None:
                last_nummer = (
                    Sitzung.objects.filter(legislatur=self.legislatur)
                    .select_for_update()  # Prevent race conditions
                    .order_by("-nummer")
                    .values_list("nummer", flat=True)
                    .first()
                )
                self.nummer = (last_nummer or 0) + 1

            # Run validation
            self.full_clean()

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Sitzung ({self.legislatur.nummer}) {self.nummer}"


# Ein selbständiger Antrag

statuschoices = {
    "B": "In Beratung",
    "A": "Angenommen",
    "N": "Abgelehnt",
    "Z": "Zurückgezogen",
    "X": "Nicht behandelt",
    "P": "Vom Präsidium zurückgewiesen",
}


class Antrag(models.Model):
    typchoices = {
        "F": "Finanzantrag",
        "S": "SatzungOrdnungsänderungsantrag",
        "P": "Positionierungsantrag",
        "A": "Antrag",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legislatur = models.ForeignKey(
        "Legislatur",
        on_delete=models.CASCADE,
        editable=False,
    )
    nummer = models.IntegerField(
        help_text="Nummer des Antrags in der Legislatur",
        validators=[MinValueValidator(1)],
        editable=False,
        null=True,
    )
    titel = models.CharField(max_length=300, help_text="Antragstitel")
    typ = models.CharField(
        max_length=1,
        choices=typchoices,
        default="A",
    )
    text = models.TextField(help_text="Antragstext", max_length=20000)
    begruendung = models.TextField(help_text="Begründung des Antrags", max_length=40000)
    minlesungen = models.IntegerField(
        help_text="Minimal nötige Lesungen bis zur Abstimmung",
        validators=[MinValueValidator(1)],
    )
    antragssumme = models.DecimalField(
        blank=True, null=True, max_digits=8, decimal_places=2
    )
    haushaltsposten = models.CharField(
        blank=True,
        null=True,
        max_length=10,
        help_text="Aus welchem Haushaltsposten wird Geld beantragt (nur Kennummer)?",
    )
    synopse = models.FileField(
        upload_to=lambda instance,
        filename: f"{instance.id}/synopse/{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}",
        help_text="Synopse bei Änderung von Ordnungen oder Satzungen",
    )
    anhang = models.FileField(
        upload_to=lambda instance,
        filename: f"{instance.id}/anhang/{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}",
        help_text="Anhang an den Antrag",
    )
    antragssteller = models.CharField(
        max_length=500, help_text="Antragssteller:innen (Name, HSG, Gremium...)"
    )
    kontaktemail = models.EmailField(
        help_text="Emailadresse für automatische Updates und Nachfragen"
    )
    kontaktperson = models.CharField(
        max_length=100, help_text="Eine spezifische Kontaktperson für Nachfragen"
    )
    status = models.CharField(max_length=1, choices=statuschoices, default="B")
    system_eingereicht = models.DateTimeField(auto_now_add=True, editable=False)
    formell_eingereicht = models.DateTimeField(
        help_text="Formelles Einreichdatum für Priorisierung, Fristen etc"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["legislatur", "nummer"],
                name="unique_legislatur_nummer_antrag",
            )
        ]

    def clean(self):
        """Ensure that formell_eingereicht date is within the legislatur period."""
        if self.legislatur_id and self.formell_eingereicht:
            if not (
                self.legislatur.anfangsdatum
                <= self.formell_eingereicht.date()
                <= self.legislatur.enddatum
            ):
                raise ValidationError(
                    {
                        "formell_eingereicht": f"Das Datum {self.formell_eingereicht.date()} liegt nicht innerhalb "
                        f"der Legislaturperiode {self.legislatur.anfangsdatum} bis {self.legislatur.enddatum}."
                    }
                )
        if self.typ == "F" and not self.antragssumme > 0:
            raise ValidationError(
                {
                    "antragssumme": "Bei Finanzanträgen muss eine (positive) Geldsumme angegeben werden"
                }
            )
        if self.typ == "F" and not self.haushaltsposten:
            raise ValidationError(
                {
                    "haushaltsposten": "Bei Finanzanträgen muss ein Haushaltsposten angegeben werden, im Zweifel kann das Finanzteam beraten"
                }
            )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Auto-select latest legislatur if not given
            if self.legislatur_id is None:
                latest_legislatur = Legislatur.objects.order_by("-nummer").first()
                if latest_legislatur is None:
                    raise ValueError("No Legislatur exists to assign to Antrag.")
                self.legislatur = latest_legislatur

            # Auto-assign nummer if not given
            if self.nummer is None:
                last_nummer = (
                    Antrag.objects.filter(legislatur=self.legislatur)
                    .select_for_update()
                    .order_by("-nummer")
                    .values_list("nummer", flat=True)
                    .first()
                )
                self.nummer = (last_nummer or 0) + 1

            # Run validation
            self.full_clean()

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Antrag {self.legislatur.nummer}/{self.nummer}: {self.titel}"


class Unterantrag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hauptantrag = models.ForeignKey(
        "Antrag",
        on_delete=models.CASCADE,
        limit_choices_to={"status": "B"},  # restricts dropdown choices in forms/admin
    )
    nummer = models.IntegerField(
        help_text="Nummer des Subantrags",
        validators=[MinValueValidator(1)],
        editable=False,
        null=True,
    )
    titel = models.CharField(max_length=300, help_text="Antragstitel")
    text = models.TextField(help_text="Antragstext", max_length=20000)
    begruendung = models.TextField(help_text="Begründung des Antrags", max_length=40000)
    antragssteller = models.CharField(
        max_length=500, help_text="Antragssteller:innen (Name, HSG, Gremium...)"
    )
    kontaktemail = models.EmailField(
        help_text="Emailadresse für automatische Updates und Nachfragen"
    )
    kontaktperson = models.CharField(
        max_length=100, help_text="Eine spezifische Kontaktperson für Nachfragen"
    )
    status = models.CharField(max_length=1, choices=statuschoices, default="B")
    system_eingereicht = models.DateTimeField(auto_now_add=True, editable=False)
    formell_eingereicht = models.DateTimeField(auto_now_add=True)
    anhang = models.FileField(
        upload_to=lambda instance,
        filename: f"{instance.id}/anhang/{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}",
        help_text="Anhang an den Änderungsantrag",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hauptantrag", "nummer"],
                name="unique_hauptantrag_nummer_unterantrag",
            )
        ]
        ordering = ["hauptantrag__legislatur__nummer", "hauptantrag__nummer", "nummer"]

    def clean(self):
        """Ensure that hauptantrag is still in status 'B' (In Beratung)."""
        if self.hauptantrag and self.hauptantrag.status != "B":
            raise ValidationError(
                {
                    "hauptantrag": f"Der Hauptantrag {self.hauptantrag} ist nicht mehr in Beratung (Status '{self.hauptantrag.get_status_display()}')."
                }
            )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.nummer is None:
                last_nummer = (
                    Unterantrag.objects.filter(hauptantrag=self.hauptantrag)
                    .select_for_update()
                    .order_by("-nummer")
                    .values_list("nummer", flat=True)
                    .first()
                )
                self.nummer = (last_nummer or 0) + 1

            # Ensure our validation is enforced
            self.full_clean()

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Unterantrag {self.hauptantrag.legislatur.nummer}/{self.hauptantrag.nummer}.{self.nummer}: {self.hauptantrag.titel} / {self.titel}"


class Lesung(models.Model):
    lesungresultchoices = {
        "AV": "Softwarevorschlag",
        "NN": "Noch nicht gelesen",
        "E": "Erfolgreich gelesen",
        "V": "Manuell Vertagt",
        "ZV": "Wegen Ende der Sitzung vertagt",
        "B": "Wegen Beschlussunfähigkeit vertagt",
        "A": "Abgestimmt",
        "T": "Schwebende Lesung / als Tischvorlage",
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    antrag = models.ForeignKey(Antrag, on_delete=models.CASCADE)
    sitzung = models.ForeignKey(Sitzung, on_delete=models.CASCADE)
    protokolleintraege = models.TextField(
        blank=True,
        help_text="Protokolleinträge zur Lesung, z.B. Diskussionsnotizen, GO-Anträge",
        max_length=50000,
    )

    abstimmbar = models.BooleanField(
        blank=True,
        Null=True,
        help_text="Kann bei dieser Lesung planmäßig abgestimmt werden?",
        editable=False,
    )

    dringlichkeit_beantragt = models.BooleanField(
        blank=True,
        null=True,
        default=False,
        help_text="Könnte in dieser Lesung abgestimmt werden, wenn ein Dringlichkeitsantrag angeommen wird?",
    )
    status = models.CharField(
        max_length=2,
        choices=lesungresultchoices,
        help_text="In Welchem Status ist die Lesung",
        default="NN",
    )

    class Meta:
        unique_together = ("antrag", "sitzung")
        ordering = ["antrag__legislatur__nummer", "antrag__nummer", "sitzung__nummer"]

    def clean(self):
        # Ensure Sitzung and Antrag belong to the same Legislatur
        if self.sitzung.legislatur != self.antrag.legislatur:
            raise ValidationError(
                "Die Sitzung und der Antrag müssen in derselben Legislaturperiode liegen."
            )
        if (
            Lesung.objects.filter(
                antrag=self.antrag,
                status="A",
                sitzung__nummer__lt=self.sitzung.nummer,
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                'Bei einer vorherigen Sitzung wurde dieser Antrag bereits abgestimmt. Falls es um eine Wiederholung der Abstimmung geht, bitte vorher status der vorherigen Lesung auf "Erfolgreich gelesen" ändern.'
            )

        if self.sitzung.anfang > timezone.now():
            allowed_pre_sitzung_status = {"AV", "NN", "T"}
            if self.status not in allowed_pre_sitzung_status:
                raise ValidationError(
                    {
                        "status": (
                            f"Vor Beginn der Sitzung darf der Status nur einer von "
                            f"{', '.join(allowed_pre_sitzung_status)} sein."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        previous_successful = Lesung.objects.filter(
            antrag=self.antrag,
            status="E",
            sitzung__nummer__lt=self.sitzung.nummer,
        ).count()

        self.abstimmbar = previous_successful >= self.antrag.minlesungen - 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lesung zu {self.antrag} in Sitzung {self.sitzung.nummer}, {self.get_status_display()}"
