# from django.contrib import admin
#
# from .models.dokumente import Vorlage, Antrag, Finanzantrag, SOAntrag, Anhang
# from .models.organisation import Faden, Schiffchen, Lesung
# from .models.sitzungen import Legislatur, Sitzung, Sondersitzung
# from .models.tagesordnung import Tagesordnungspunkt, Tischvorlage
#
#
# @admin.register(Legislatur)
# class LegislaturAdmin(admin.ModelAdmin):
#    list_display = ("nummer", "anfang", "ende")
#    ordering = ("nummer",)
#
#
# @admin.register(Sitzung)
# class SitzungAdmin(admin.ModelAdmin):
#    list_display = ("nummer", "legislatur", "anfang", "ende", "ort")
#    list_filter = ("legislatur",)
#    ordering = ("legislatur", "nummer")
#    date_hierarchy = "anfang"
#
#
# @admin.register(Sondersitzung)
# class SondersitzungAdmin(admin.ModelAdmin):
#    list_display = ("nummer", "legislatur", "anfang", "ende", "ort")
#    list_filter = ("legislatur",)
#    ordering = ("legislatur", "nummer")
#    date_hierarchy = "anfang"
#
#
# @admin.register(Faden)
# class FadenAdmin(admin.ModelAdmin):
#    list_display = ("id", "kontaktperson", "email", "aktuelle_vl", "ueberfaden")
#    search_fields = ("kontaktperson", "email")
#
#
# @admin.register(Schiffchen)
# class SchiffchenAdmin(admin.ModelAdmin):
#    list_display = ("id", "legislatur", "hauptfaden", "erwartete_lesungen")
#    list_filter = ("legislatur",)
#
#
# @admin.register(Lesung)
# class LesungAdmin(admin.ModelAdmin):
#    list_display = ("id", "schiffchen", "dringlichkeit_beantragt")
#    list_filter = ("dringlichkeit_beantragt",)
#
#
# @admin.register(Vorlage)
# class VorlageAdmin(admin.ModelAdmin):
#    list_display = ("id", "titel", "faden", "eingereicht_organisatorisch", "zeigen")
#    list_filter = ("zeigen",)
#    search_fields = ("titel",)
#
#
# @admin.register(Antrag)
# class AntragAdmin(admin.ModelAdmin):
#    list_display = ("id", "titel", "antragssteller", "faden")
#    search_fields = ("titel", "antragssteller")
#
#
# @admin.register(Finanzantrag)
# class FinanzantragAdmin(admin.ModelAdmin):
#    list_display = ("id", "titel", "antragssteller", "antragssumme", "faden")
#    search_fields = ("titel", "antragssteller")
#
#
# @admin.register(SOAntrag)
# class SOAntragAdmin(admin.ModelAdmin):
#    list_display = ("id", "titel", "antragssteller", "orgsatzungsaenderung", "faden")
#    search_fields = ("titel", "antragssteller")
#
#
# @admin.register(Anhang)
# class AnhangAdmin(admin.ModelAdmin):
#    list_display = ("id", "titel", "faden", "hochgeladen_am", "zeigen")
#    list_filter = ("zeigen",)
#    search_fields = ("titel",)
#
#
# @admin.register(Tagesordnungspunkt)
# class TagesordnungspunktAdmin(admin.ModelAdmin):
#    list_display = ("id", "sitzung", "nummer", "ergebnis")
#    list_filter = ("sitzung", "ergebnis")
#
#
# @admin.register(Tischvorlage)
# class TischvorlageAdmin(admin.ModelAdmin):
#    list_display = ("id", "sitzung", "nummer", "angenommen")
#    list_filter = ("sitzung", "angenommen")
#
