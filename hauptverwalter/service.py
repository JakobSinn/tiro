from .models.dokumente import Vorlage, Finanzantrag, SOAntrag, Antrag
from .models.sitzungen import Legislatur, Sitzung
from .models.organisation import Schiffchen, Lesung, Faden
from .models.tagesordnung import Tagesordnungspunkt


def make_aktuelle_vorlage(unsere_vorlage: Vorlage):
    unser_faden = unsere_vorlage.faden
    if not unser_faden:
        return 0
    if unser_faden.aktuelle_vorlage == unsere_vorlage:
        return 1
    else:
        unser_faden.aktuelle_vorlage = unsere_vorlage
        unser_faden.full_clean()
        unser_faden.save()
        return 1


def get_current_legislature_nr():
    aktuell = Legislatur.objects.order_by("-nummer").first()
    if not aktuell:
        return 1
    return aktuell.nummer


def get_current_legislature():
    return Legislatur.objects.order_by("-nummer").first()


def get_active_schiffchen(gesuchte_legislatur: Legislatur):
    """Gibt dict mit id von Schiffchen als key aus, das alle Schiffchen der legislatur, die noch keinen TOP mit Status "A" (Abgestimmt/Entschieden) haben, aus"""
    if gesuchte_legislatur is None:
        return None
    else:
        return (
            Schiffchen.objects.filter(legislatur=gesuchte_legislatur)
            .exclude(lesungen__tagesordnungspunkte__ergebnis="A")
            .distinct()
            .in_bulk()
        )


def make_new_top(behandeltes_schiffchen: Schiffchen, behandelte_sitzung: Sitzung):
    if not behandeltes_schiffchen:
        return None
    if not behandelte_sitzung:
        return None
    unsere_lesung = (
        behandeltes_schiffchen.lesungen.exclude(
            tagesordnungspunkte__ergebnis__in=["A", "E"]
        )
        .order_by("id")
        .first()
    )
    if not unsere_lesung:
        unsere_lesung = Lesung.objects.create(schiffchen=behandeltes_schiffchen)
    Tagesordnungspunkt.objects.create(sitzung=behandelte_sitzung, lesung=unsere_lesung)


def count_unterfaeden(aktueller_faden: Faden):
    if aktueller_faden is None:
        return 0
    if aktueller_faden.unterfaeden.first() is None:
        return 0
    result = 0
    for unterf in aktueller_faden.unterfaeden.in_bulk().values():
        result = result + 1
        result = result + count_unterfaeden(unterf)
    else:
        return result
    return 0


def new_faden(
    email: str,
    kontaktperson: str,
    titel: str,
    text: str,
    antragssteller: str | None = None,
    begruendung: str | None = None,
    posten: str | None = None,
    antragssumme: float | None = None,
    orgsatzungsaenderung: bool = False,
    satzung: str | None = None,
    ueberfaden: Faden | None = None,
    lesungen: int | None = None,
):
    """Richtet einen neuen Faden, falls nötig ein Schiffchen und eine Vorlage ein, und verbindet sie alle miteinander. Um einem schon existierenden Antrag (Faden) eine neue Version (Vorlage) zu geben kann diese Funktion nicht verwendet werden."""
    assert get_current_legislature()
    faden_kwargs = {"email": email, "kontaktperson": kontaktperson}
    if ueberfaden is not None:
        faden_kwargs["ueberfaden"] = ueberfaden
    unser_faden = Faden.objects.create(**faden_kwargs)
    if not ueberfaden:
        # ein neues Schiffchen wird wenn nötig eingerichtet
        lesungen_benötigt = 2
        if antragssumme and antragssumme <= 600:
            # Finanzanträge unter 600€ haben automatisch nur eine Lesung, alle anderen ausnahmen können im nachhienein vom Präsidium festgestellt werden
            lesungen_benötigt = 1
        if lesungen:
            # falls in parametern der fkt die benötigten Lesungen manuell gesetzt wurden, dass übernehmen
            lesungen_benötigt = lesungen
        Schiffchen.objects.create(
            hauptfaden=unser_faden,
            legislatur=get_current_legislature(),
            erwartete_lesungen=lesungen_benötigt,
        )
    if antragssumme:
        unsere_vorlage = Finanzantrag.objects.create(
            faden=unser_faden,
            antragssteller=antragssteller if antragssteller else "",
            antragssumme=antragssumme,
            haushaltsposten=posten if posten else "",
            text=text,
            titel=titel,
            begruendung=begruendung if begruendung else "",
        )
    elif satzung:
        unsere_vorlage = SOAntrag.objects.create(
            faden=unser_faden,
            antragssteller=antragssteller if antragssteller else "",
            zu_aendernde_satzung=satzung,
            text=text,
            titel=titel,
            begruendung=begruendung if begruendung else "",
            orgsatzungsaenderung=orgsatzungsaenderung,
        )
    elif begruendung:
        unsere_vorlage = Antrag.objects.create(
            faden=unser_faden,
            antragssteller=antragssteller if antragssteller else "",
            text=text,
            titel=titel,
            begruendung=begruendung,
        )
    else:
        unsere_vorlage = Vorlage.objects.create(
            faden=unser_faden,
            text=text,
            titel=titel,
        )
    if unsere_vorlage:
        make_aktuelle_vorlage(unsere_vorlage)
