from django import forms
from .models_alt import Antrag


class Step1Form(forms.Form):
    """First step: submitter contact info and request type."""

    TYPE_CHOICES = (
        ("F", "Finanzantrag"),
        ("S", "Satzung / Ordnungsänderung"),
        ("P", "Positionierung"),
        ("B", "Bericht / Diskussion"),
        ("A", "Allgemeiner Antrag"),
    )

    antragssteller = forms.CharField(max_length=500, label="Formelle Antragssteller:in")
    kontaktperson = forms.CharField(max_length=100, required=False)
    kontaktemail = forms.EmailField(label="Kontakt E‑Mail")
    wants_updates = forms.BooleanField(
        required=False,
        initial=True,
        label="Auto-E-Mails bekommen",
        help_text="Möchtest du automatische E-Mails bekommen, wenn z.B. eine Lesung deines Antrags/Berichts angesetzt wird?",
    )
    typ = forms.ChoiceField(choices=TYPE_CHOICES, label="Antragstyp")


class Step2Form(forms.ModelForm):
    """Second step: the Antrag content. ModelForm for Antrag. Server enforces per-type rules in clean()."""

    class Meta:
        model = Antrag
        fields = [
            "typ",
            "titel",
            "text",
            "begruendung",
            "anhang",
            "synopse",
            "antragssumme",
            "haushaltsposten",
            "orgsatzungsaenderung",
        ]
        labels = {"text": "Zu beschliessender Antragstext"}

    def __init__(self, *args, **kwargs):
        # allow the view to pass the chosen typ via kwargs for initialisation
        self.selected_typ = kwargs.pop("selected_typ", None)
        super().__init__(*args, **kwargs)

        # Determine active typ from supplied kwarg, bound data (POST), or initial
        typ = self.selected_typ
        if not typ:
            # POSTed data may include the typ from step1; try to read it
            try:
                # self.data is a QueryDict when bound
                typ = self.data.get("typ") or self.data.get(self.add_prefix("typ"))
            except Exception:
                typ = None
        if not typ:
            typ = self.initial.get("typ")

        # Ensure the hidden typ field exists and reflects the chosen type
        if "typ" in self.fields:
            from django.forms import HiddenInput

            self.fields["typ"].widget = HiddenInput()
            if typ:
                self.initial.setdefault("typ", typ)

        # Fields that are always shown
        common = {"typ", "titel", "text", "begruendung", "anhang"}

        # Per-type additional fields
        type_fields = {
            "F": {"antragssumme", "haushaltsposten"},
            "S": {"synopse", "orgsatzungsaenderung"},
            "P": set(),
            "B": set(),
            "A": set(),
        }

        # Decide which fields to keep
        keep = set(common)
        if typ in type_fields:
            keep |= type_fields.get(typ, set())
        else:
            # default: show all fields if typ unknown
            keep = set(self.fields.keys())

        # Adjust required flags for UX (final checks remain in clean())
        if typ == "F":
            if "antragssumme" in self.fields:
                self.fields["antragssumme"].required = True
            if "haushaltsposten" in self.fields:
                self.fields["haushaltsposten"].required = True

        # Remove non-relevant fields from the form so templates only render necessary inputs
        for fname in list(self.fields.keys()):
            if fname not in keep:
                self.fields.pop(fname, None)

    def clean(self):
        cleaned = super().clean()
        typ = self.selected_typ or self.data.get("typ") or self.initial.get("typ")
        # Finanzantrag checks
        if typ == "F":
            s = cleaned.get("antragssumme")
            p = cleaned.get("haushaltsposten")
            if s is None or s <= 0:
                self.add_error(
                    "antragssumme",
                    "Bei Finanzanträgen muss eine positive Summe angegeben werden.",
                )
            if not p:
                self.add_error(
                    "haushaltsposten",
                    "Bei Finanzanträgen muss ein Haushaltsposten angegeben werden.",
                )

        # Satzungsänderung expects synopse when orgsatzungsaenderung true
        if typ == "S":
            if cleaned.get("orgsatzungsaenderung") and not cleaned.get("synopse"):
                self.add_error(
                    "synopse",
                    "Bei Änderungen der Organisationssatzung bitte eine Synopse hochladen.",
                )

        return cleaned
