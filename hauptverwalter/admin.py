from django.contrib import admin
from hauptverwalter.models.dokumente import (
    Vorlage,
    Antrag,
    Finanzantrag,
    SOAntrag,
    Anhang,
)
from hauptverwalter.models.organisation import Faden, Schiffchen, Lesung
from hauptverwalter.models.sitzungen import Legislatur, Sitzung, Sondersitzung
from hauptverwalter.models.tagesordnung import Tagesordnungspunkt, Tischvorlage

admin.site.register(Vorlage)
admin.site.register(Antrag)
admin.site.register(Finanzantrag)
admin.site.register(SOAntrag)
admin.site.register(Anhang)
admin.site.register(Faden)
admin.site.register(Schiffchen)
admin.site.register(Lesung)
admin.site.register(Sitzung)
admin.site.register(Sondersitzung)
admin.site.register(Legislatur)
admin.site.register(Tagesordnungspunkt)
admin.site.register(Tischvorlage)
