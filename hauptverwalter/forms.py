from django import forms


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


class Step2Form(forms.Form):
    """Second step: Antrag/Vorlage content. Server enforces per-type rules in clean()."""

    typ = forms.CharField(required=False)
    titel = forms.CharField(max_length=255)
    text = forms.CharField(widget=forms.Textarea, max_length=20000)
    begruendung = forms.CharField(widget=forms.Textarea, max_length=40000)
    anhang = forms.FileField(required=False)
    antragssumme = forms.DecimalField(required=False, max_digits=20, decimal_places=2)
    haushaltsposten = forms.CharField(required=False, max_length=10)
    orgsatzungsaenderung = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.selected_typ = kwargs.pop("selected_typ", None)
        super().__init__(*args, **kwargs)

        typ = self.selected_typ
        if not typ:
            try:
                typ = self.data.get("typ") or self.data.get(self.add_prefix("typ"))
            except Exception:
                typ = None
        if not typ:
            typ = self.initial.get("typ")

        if "typ" in self.fields:
            from django.forms import HiddenInput

            self.fields["typ"].widget = HiddenInput()
            if typ:
                self.initial.setdefault("typ", typ)

        common = {"typ", "titel", "text", "begruendung", "anhang"}
        type_fields = {
            "F": {"antragssumme", "haushaltsposten"},
            "S": {"orgsatzungsaenderung"},
            "P": set(),
            "B": set(),
            "A": set(),
        }

        keep = set(common)
        if typ in type_fields:
            keep |= type_fields.get(typ, set())
        else:
            keep = set(self.fields.keys())

        if typ == "F":
            if "antragssumme" in self.fields:
                self.fields["antragssumme"].required = True
            if "haushaltsposten" in self.fields:
                self.fields["haushaltsposten"].required = True

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


class BasicAntragForm(forms.Form):
    """Single-step form for basic Antrag submission without the wizard."""

    typ = forms.CharField(required=False)
    antragssteller = forms.CharField(max_length=500, label="Formelle Antragssteller:in")
    kontaktperson = forms.CharField(max_length=100, required=False)
    kontaktemail = forms.EmailField(label="Kontakt E-Mail")
    titel = forms.CharField(max_length=255, required=False)
    text = forms.CharField(widget=forms.Textarea, max_length=20000)
    begruendung = forms.CharField(widget=forms.Textarea, max_length=40000)
    anhang = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.forms import HiddenInput

        self.fields["typ"].widget = HiddenInput()
        self.initial.setdefault("typ", "A")

    def clean(self):
        cleaned = super().clean()
        titel = cleaned.get("titel")
        if not titel:
            text = cleaned.get("text") or ""
            first_line = next((line for line in text.splitlines() if line.strip()), "")
            cleaned["titel"] = first_line[:255] or "Antrag"
        return cleaned
