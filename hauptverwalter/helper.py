from typing import List
from .models_alt import Lesung, Sitzung, TOPname, TOPBlock


def buildTOPs(sitzung: Sitzung) -> List[dict]:
    """Group Lesungen into TOP blocks for the given Sitzung.

    Prefer explicit TOPBlock grouping when available (new model). If TOPBlock
    relations are not populated yet, fall back to old prio/TOPname grouping to
    preserve existing behavior during migration.
    """
    # If TOPBlock objects exist for this Sitzung, use them (ordered by 'order')
    topblocks = list(TOPBlock.objects.filter(sitzung=sitzung).order_by("order"))

    if topblocks:
        grouped = []
        for tb in topblocks:
            lesungen = list(
                tb.lesungen.select_related("antrag").order_by(
                    "antrag__formell_eingereicht"
                )
            )
            grouped.append({"titel": tb.titel, "lesungen": lesungen})
        return grouped

    # Fallback: old behavior
    lesungen = (
        Lesung.objects.filter(sitzung=sitzung)
        .select_related("antrag")
        .order_by("prio", "antrag__formell_eingereicht")
    )

    # Load TOP names once and index by prio
    topnames_by_prio = {
        top.prio: top.name for top in TOPname.objects.filter(sitzung=sitzung)
    }

    grouped = []
    current_priority = None
    priority_block = None
    top_counter = 0  # laufende TOP-Nummer

    for lesung in lesungen:
        if lesung.prio != current_priority:
            current_priority = lesung.prio
            if topnames_by_prio.get(current_priority) or not grouped:
                top_counter += 1
                titel = "TOP " + topnames_by_prio.get(
                    current_priority,
                    "Erster TOP (Prio " + str(current_priority) + ")",
                )
                priority_block = {
                    "prio": current_priority,
                    "titel": titel,
                    "lesungen": [],
                }
                grouped.append(priority_block)
        priority_block["lesungen"].append(lesung)

    return grouped
