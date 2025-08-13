from django.contrib import admin
from .models import Legislatur, Sitzung, Antrag, Unterantrag, Lesung


# -------------------
# Shared helper
# -------------------
def add_nummer_help_text(field_dict):
    """Utility: Add auto-assignment help text to nummer fields."""
    if "nummer" in field_dict:
        field_dict["nummer"].help_text = "(will be assigned automatically)"


# -------------------
# Unterantrag
# -------------------
class UnterantragInline(admin.TabularInline):
    model = Unterantrag
    extra = 0
    readonly_fields = ("nummer",)

    def has_add_permission(self, request, obj=None):
        if obj and obj.status != "B":
            return False
        return super().has_add_permission(request, obj)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        add_nummer_help_text(formset.form.base_fields)
        return formset


@admin.register(Unterantrag)
class UnterantragAdmin(admin.ModelAdmin):
    list_display = ("__str__", "hauptantrag", "nummer", "status")
    list_filter = ("status", "hauptantrag__legislatur")
    search_fields = ("titel", "hauptantrag__titel")
    ordering = ("hauptantrag", "nummer")
    readonly_fields = ("nummer",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "hauptantrag":
            kwargs["queryset"] = Antrag.objects.filter(status="B")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        add_nummer_help_text(form.base_fields)
        return form


# -------------------
# Antrag
# -------------------
class AntragInline(admin.TabularInline):
    model = Antrag
    extra = 0
    readonly_fields = ("nummer",)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        add_nummer_help_text(formset.form.base_fields)
        return formset


@admin.register(Antrag)
class AntragAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "legislatur", "nummer")
    list_filter = ("status", "legislatur")
    search_fields = ("titel",)
    ordering = ("legislatur", "nummer")
    inlines = [UnterantragInline]
    readonly_fields = ("nummer",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        add_nummer_help_text(form.base_fields)
        return form

    def get_inline_instances(self, request, obj=None):
        if obj and obj.status != "B":
            return []
        return super().get_inline_instances(request, obj)


# -------------------
# Sitzung
# -------------------
@admin.register(Sitzung)
class SitzungAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "legislatur",
        "nummer",
        "anfang",
        "ende",
        "sondersitzung",
    )
    list_filter = ("legislatur", "sondersitzung")
    ordering = ("legislatur", "nummer")
    readonly_fields = ("nummer",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        add_nummer_help_text(form.base_fields)
        return form


# -------------------
# Legislatur
# -------------------
@admin.register(Legislatur)
class LegislaturAdmin(admin.ModelAdmin):
    list_display = ("nummer", "anfangsdatum", "enddatum")
    ordering = ("nummer",)


@admin.register(Lesung)
class LesungAdmin(admin.ModelAdmin):
    list_display = ("antrag", "sitzung", "get_legislatur")
    list_filter = (
        "antrag__legislatur",
        "sitzung__legislatur",
        "dringlichkeit_beantragt",
        "abstimmbar",
    )
    search_fields = ("antrag__titel", "protokolleintraege")

    def get_legislatur(self, obj):
        return obj.antrag.legislatur

    get_legislatur.short_description = "Legislatur"

    # Optional: limit Sitzung queryset to match Antrag's Legislatur in admin form
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "sitzung" and request.resolver_match.kwargs.get(
            "object_id"
        ):
            obj_id = request.resolver_match.kwargs["object_id"]
            try:
                obj = self.model.objects.get(pk=obj_id)
                kwargs["queryset"] = Sitzung.objects.filter(
                    legislatur=obj.antrag.legislatur
                )
            except self.model.DoesNotExist:
                pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
