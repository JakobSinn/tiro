from typing import List
from .models import Lesung, Sitzung, TOPname


def buildTOPs(sitzung: Sitzung) -> List[dict]:
    lesungen = (
        Lesung.objects.filter(sitzung=sitzung)
        .select_related("antrag")
        .order_by("prio", "-antrag__formell_eingereicht")
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
            top_counter += 1

            titel = (
                "TOP "
                + str(top_counter)
                + ": "
                + topnames_by_prio.get(
                    current_priority,
                    "",
                )
            )

            priority_block = {
                "prio": current_priority,
                "titel": titel,
                "lesungen": [],
            }
            grouped.append(priority_block)

        priority_block["lesungen"].append(lesung)

    return grouped
