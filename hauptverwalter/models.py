from django.db import models, transaction
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
import uuid
import os


# --- helpers (kept as before) -----------------------------------------------


def makeuploadpathanhang(instance, filename):
    """Create a file path for 'anhang' files using the instance id and slugified name."""
    return f"{instance.id}/anhang/{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}"


def makeuploadpatsynopse(instance, filename):
    """Create a file path for 'synopse' files using the instance id and slugified name."""
    return f"{instance.id}/synopse/{slugify(os.path.splitext(filename)[0])}{os.path.splitext(filename)[1]}"


# --- core models (unchanged semantics) -------------------------------------


class Legislatur(models.Model):
    """Represents a StuRa legislature period; Sitzungen and Anträge belong to this."""

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


# --- mixins & abstract bases -----------------------------------------------


class UUIDPrimaryKeyMixin(models.Model):
    """Mixin that provides a UUID primary key field named `id`."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class FileAttachmentMixin(models.Model):
    """
    Mixin that adds common file attachments.
    Note: both 'anhang' and 'synopse' are provided; subclasses may use or ignore them.
    """

    anhang = models.FileField(
        upload_to=makeuploadpathanhang,
        help_text="Anhang an den Antrag / Unterantrag",
        blank=True,
        null=True,
    )
    synopse = models.FileField(
        upload_to=makeuploadpatsynopse,
        help_text="Synopse bei Änderung von Ordnungen oder Satzungen (falls relevant)",
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True


class AntragBase(UUIDPrimaryKeyMixin, FileAttachmentMixin, models.Model):
    """
    Abstract base for Antrag and Unterantrag:
    contains shared descriptive/contact fields and basic timestamps/status.
    Subclasses should implement/extend specific validation and numbering.
    """

    statuschoices = {
        "B": "In Beratung",
        "A": "Angenommen",
        "N": "Abgelehnt",
        "Z": "Zurückgezogen",
        "X": "Nicht behandelt",
        "P": "Vom Präsidium zurückgewiesen",
    }

    titel = models.CharField(max_length=300, help_text="Antragstitel")
    text = models.TextField(help_text="Antragstext", max_length=20000)
    begruendung = models.TextField(help_text="Begründung des Antrags", max_length=40000)
    antragssteller = models.CharField(
        max_length=500,
        help_text="Formelle Antragssteller:innen (Name, HSG, Gremium...)",
    )
    kontaktemail = models.EmailField(
        help_text="Emailadresse für automatische Updates und Nachfragen, wird nicht veröffentlicht"
    )
    kontaktperson = models.CharField(
        max_length=100,
        help_text="Eine spezifische Kontaktperson für Nachfragen, wird nicht veröffentlicht",
        blank=True,
    )
    status = models.CharField(max_length=1, choices=statuschoices, default="B")
    system_eingereicht = models.DateTimeField(auto_now_add=True, editable=False)
    formell_eingereicht = models.DateTimeField(
        help_text="Formelles Einreichdatum für Priorisierung, Fristen etc",
        auto_now_add=True,
    )
    anmerkungen_extern = models.TextField(
        max_length=10000,
        blank=True,
        help_text="Von außen lesbare Anmerkungen des Präsidiums",
    )

    anmerkungen_intern = models.TextField(
        max_length=10000,
        blank=True,
        help_text="Von außen _nicht_ lesbare Anmerkungen des Präsidiums",
    )

    class Meta:
        abstract = True

    def make_angenommen(self):
        with transaction.atomic():
            self.status = "A"
            self.save()

    def make_abgelehnt(self):
        with transaction.atomic():
            self.status = "N"
            self.save()

    def __str__(self):
        # Concrete subclasses may override or extend this
        return f"{self.titel} ({self.get_status_display()})"


# --- concrete models with numbering kept inside each class ------------------


class Sitzung(UUIDPrimaryKeyMixin, models.Model):
    """A StuRa meeting (Sitzung). Assigned to a Legislatur and optionally numbered."""

    legislatur = models.ForeignKey(
        "Legislatur",
        on_delete=models.CASCADE,
        editable=False,
    )
    nummer = models.IntegerField(
        help_text="Nummer der Sitzung",
        validators=[MinValueValidator(1), MaxValueValidator(10000)],
        unique=True,
        blank=True,
        null=True,
    )
    anfang = models.DateTimeField(
        help_text="Wann beginnt die Sitzung?",
    )
    ende = models.DateTimeField(
        help_text="Wann endet(e) die Sitzung?",
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

    @property
    def is_sondersitzung(self):
        return self.sondersitzung

    @property
    def is_future(self):
        return self.anfang > timezone.now()

    @property
    def is_past(self):
        now = timezone.now()
        if self.ende:
            return self.ende < now

        local_now = timezone.localtime(now)
        heute_mitternacht = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return timezone.localtime(self.anfang) < heute_mitternacht

    @property
    def is_running(self):
        return not (self.is_past or self.is_future)

    @property
    def nummer_in_legislatur(self):
        bisher_in_legislatur = (
            Sitzung.objects.filter(legislatur=self.legislatur)
            .filter(nummer__lt=self.nummer)
            .count()
        )
        return (bisher_in_legislatur or 0) + 1

    class Meta:
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

        if self.ende and self.anfang > self.ende:
            raise ValidationError(
                {"ende": "Die Sitzung kann nicht enden bevor sie begonnen hat"}
            )

    def save(self, *args, **kwargs):
        """Assign latest legislatur if missing and auto-assign global nummer if missing."""
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
                    Sitzung.objects.select_for_update()
                    .order_by("-nummer")
                    .values_list("nummer", flat=True)
                    .first()
                )
                self.nummer = (last_nummer or 0) + 1

            # Run validation
            self.full_clean()

            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nummer}. StuRa-Sitzung, {self.legislatur.nummer}. Legislatur"


class Antrag(AntragBase):
    """A primary Antrag: belongs to a Legislatur."""

    typchoices = {
        "F": "Finanzantrag",
        "S": "Satzungs- oder Ordnungsänderungsantrag",
        "P": "Positionierungsantrag",
        "A": "Antrag",
    }

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
    typ = models.CharField(
        max_length=1,
        choices=typchoices,
        default="A",
    )
    minlesungen = models.IntegerField(
        help_text="Minimal nötige Lesungen bis zur Abstimmung",
        validators=[MinValueValidator(1)],
    )
    antragssumme = models.DecimalField(
        blank=True,
        null=True,
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    haushaltsposten = models.CharField(
        blank=True,
        null=True,
        max_length=10,
        help_text="Aus welchem Haushaltsposten wird Geld beantragt (nur Kennummer)?",
    )
    orgsatzungsaenderung = models.BooleanField(
        blank=True,
        help_text="Geht es um eine Änderung der Organisationssatzung?",
        default=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["legislatur", "nummer"],
                name="unique_legislatur_nummer_antrag",
            )
        ]

    @property
    def is_finanzantrag(self):
        return self.typ == "F"

    @property
    def is_soantrag(self):
        return self.typ == "S"

    @property
    def will_orgsatzung_aendern(self):
        return self.orgsatzungsaenderung

    @property
    def beschlussfaehigkeitssicher(self):
        """
        Gibt True zurück, wenn der Antrag bereits wegen Beschlussunfähigkeit vertagt wurde
        (d.h. eine Lesung mit status='B' existiert)
        und keine Änderung der Organisationssatzung geplant ist. (siehe §15 (4, 5) der StuRa-Geschäftsordnung)
        """
        # Prüfen, ob es Lesungen gibt, die wegen Beschlussunfähigkeit vertagt wurden
        hat_beschlussunfaehige_lesung = self.lesung_set.filter(status="B").exists()

        return hat_beschlussunfaehige_lesung and not self.will_orgsatzung_aendern

    @property
    def default_prio(self):
        if self.will_orgsatzung_aendern:
            return 300
        if self.is_soantrag:
            return 400
        if self.is_finanzantrag:
            return 500
        return 700

    def clean(self):
        """Validation specific to Antrag (keeps original business rules)."""
        # Ensure that formell_eingereicht date is within the legislatur period
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
        if self.is_finanzantrag and not (self.antragssumme or 0) > 0:
            raise ValidationError(
                {
                    "antragssumme": "Bei Finanzanträgen muss eine (positive) Geldsumme angegeben werden"
                }
            )
        if self.is_finanzantrag and not self.haushaltsposten:
            raise ValidationError(
                {
                    "haushaltsposten": "Bei Finanzanträgen muss ein Haushaltsposten angegeben werden, im Zweifel kann das Finanzteam beraten"
                }
            )
        if not self.is_finanzantrag and (self.antragssumme or 0) > 0:
            raise ValidationError(
                {
                    "antragssumme": "Eine Antragssumme kann nur bei Finanzanträgen angegeben werden"
                }
            )
        if not self.is_finanzantrag and self.haushaltsposten:
            raise ValidationError(
                {
                    "haushaltsposten": "Ein Haushaltsposten kann nur bei Finanzanträgen angegeben werden"
                }
            )
        if self.will_orgsatzung_aendern and not self.is_soantrag:
            raise ValidationError(
                {
                    "orgsatzungsaenderung": "Nur Ordungs/Satzungsänderungsanträge können als die Orgsatzung ändernd markiert werden."
                }
            )
        if self.synopse and not self.is_soantrag:
            raise ValidationError(
                {
                    "synopse": "Nur bei Änderungen an Satzungen oder Ordnungen kann eine Synopse hochgeladen werden"
                }
            )

    def save(self, *args, **kwargs):
        """Auto-select latest legislatur if not given and auto-assign nummer per legislatur."""
        with transaction.atomic():
            # Auto-select latest legislatur if not given
            if self.legislatur_id is None:
                latest_legislatur = Legislatur.objects.order_by("-nummer").first()
                if latest_legislatur is None:
                    raise ValueError("No Legislatur exists to assign to Antrag.")
                self.legislatur = latest_legislatur

            # Auto-assign nummer if not given (per legislatur)
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
        return f"{self.get_typ_display()} {self.legislatur.nummer}/{self.nummer}: {self.titel}"


class Unterantrag(AntragBase):
    """A sub-amendment to a Hauptantrag (Hauptantrag must be in status 'B')."""

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
        """Assign nummer within the hauptantrag scope."""
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

            self.full_clean()

            super().save(*args, **kwargs)

    def __str__(self):
        return f"Unterantrag {self.hauptantrag.legislatur.nummer}/{self.hauptantrag.nummer}.{self.nummer}: {self.hauptantrag.titel} / {self.titel}"


# --- Lesung remains mostly the same, using UUID mixin -----------------------


class Lesung(UUIDPrimaryKeyMixin, models.Model):
    """A reading of an Antrag in a Sitzung (tracks status, protokolleintraege, etc.)."""

    lesungresultchoices = {
        "AV": "Softwarevorschlag",
        "NN": "Noch nicht gelesen",
        "E": "Erfolgreich gelesen",
        "V": "Manuell Vertagt",
        "ZV": "Wegen Ende der Sitzung vertagt",
        "B": "Wegen Beschlussunfähigkeit vertagt",
        "A": "Abgestimmt",
        "T": "Schwebende Lesung / als Tischvorlage",
        "NT": "Aufname nach ",
    }

    antrag = models.ForeignKey(Antrag, on_delete=models.CASCADE)
    sitzung = models.ForeignKey(Sitzung, on_delete=models.CASCADE)
    protokolleintraege = models.TextField(
        blank=True,
        help_text="Protokolleinträge zur Lesung, z.B. Diskussionsnotizen, GO-Anträge",
        max_length=50000,
    )

    abstimmbar = models.BooleanField(
        blank=True,
        null=True,
        default=False,
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
    prio = models.IntegerField(
        verbose_name="Priorität",
        help_text="Niedrige Werte tauchen auf generierten Tagesordnungen früher auf",
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    @property
    def is_future(self):
        return self.status in {"AV", "NN", "T"}

    @property
    def is_tischvorlage(self):
        return self.status in {"T", "NT"}

    @property
    def is_past(self):
        return self.status in {"E", "V", "ZV", "B", "A", "NT"}

    @property
    def nummer(self):
        # die wievielte Lesung ist das (nur erfolgreiche werden gezählt)
        return (
            Lesung.objects.filter(
                antrag=self.antrag,
                sitzung__nummer__lt=self.sitzung.nummer,
                status="E",
            ).count()
            + 1
        )

    def antrag_angenommen(self):
        """Antrag wurde Angenommen in dieser Lesung"""
        with transaction.atomic():
            self.status = "A"
            self.antrag.make_angenommen()

    def antrag_abgelehnt(self):
        with transaction.atomic():
            self.status = "A"
            self.antrag.make_abgelehnt()

    def lesung_vertagt_sitzungsende(self):
        with transaction.atomic():
            self.status = "ZV"

    def lesung_vertagt_beschlussunfähig(self):
        with transaction.atomic():
            self.status = "B"

    def lesung_erfolgreich(self):
        with transaction.atomic():
            self.status = "E"

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

        if self.sitzung.anfang < self.antrag.formell_eingereicht:
            raise ValidationError(
                {
                    "sitzung": "Die Sitzung beginnt, bevor der Antrag formell eingereicht wurde"
                }
            )
        if self.antrag.orgsatzungsaenderung and self.dringlichkeit_beantragt:
            raise ValidationError(
                "Anträge, die die Orgsatzung ändern, können nicht dringlich abgestimmt werden"
            )

        if self.dringlichkeit_beantragt and self.abstimmbar:
            raise ValidationError(
                {
                    "dringlichkeit_beantragt": "Der Antrag ist schon als in dieser Lesung abstimmbar markiert - entweder vorherige Lesungen wurden fälschlich als Erfolgreich markiert oder der Dringlichkeitsantrag ist gegenstandslos"
                }
            )

        if self.sitzung.anfang > timezone.now():
            if not self.is_future:
                raise ValidationError(
                    {
                        "status": "Die Sitzung hat noch nicht begonnen - der Status macht keinen Sinn"
                    }
                )
        if self.sitzung.ende and self.sitzung.ende < timezone.now():
            if not self.is_past:
                raise ValidationError(
                    {
                        "status": "Die Sitzung ist schon zuende - der Status macht keinen Sinn"
                    }
                )

    def save(self, *args, **kwargs):
        """Ist der Antrag in dieser Lesung abstimmbar? Wenn keine Priorität manuell gegeben wurde, standardwerte annehmen"""
        previous_successful = Lesung.objects.filter(
            antrag=self.antrag,
            status="E",
            sitzung__nummer__lt=self.sitzung.nummer,
        ).count()

        self.abstimmbar = previous_successful >= self.antrag.minlesungen - 1

        if not self.prio:
            self.prio = self.antrag.default_prio

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lesung {self.nummer} von {self.antrag} in Sitzung {self.sitzung.nummer}, {self.get_status_display()}"
