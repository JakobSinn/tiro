from django.shortcuts import get_object_or_404


from .models.sitzungen import Legislatur
from .models.organisation import Schiffchen


def get_current_legislature():
    aktuell = Legislatur.objects.order_by("-nummer").first()
    if not aktuell:
        return 1
    return aktuell.nummer


def get_current_legislature_obj():
    return Legislatur.objects.order_by("-nummer").first()


def get_faden_details(schiffchen_id):
    schiffchen = get_object_or_404(Schiffchen, id=schiffchen_id)
    results = {}
    results["id"] = schiffchen.id
    results["titel"] = (
        schiffchen.hauptfaden.aktuelle_vl.titel
        if schiffchen.hauptfaden and schiffchen.hauptfaden.vorlage
        else "Kein Titel"
    )
    results["kontaktperson"] = (
        schiffchen.hauptfaden.kontaktperson
        if schiffchen.hauptfaden.kontaktperson
        else "Keine Kontaktperson"
    )
    results["kontaktemail"] = (
        schiffchen.hauptfaden.email if schiffchen.hauptfaden.email else False
    )
    results["legislatur"] = (
        schiffchen.legislatur.nummer
        if schiffchen.legislatur
        else "Keiner Legislatur zugeordnet"
    )
    results["erwartete_lesungen"] = schiffchen.erwartete_lesungen
    results[""]
