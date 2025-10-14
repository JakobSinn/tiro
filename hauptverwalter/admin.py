from django.contrib import admin, messages
from .models import Legislatur, Sitzung, Antrag, Unterantrag, Lesung
from django.db import transaction
from django.core.exceptions import ValidationError


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
    date_hierarchy = "formell_eingereicht"

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
    date_hierarchy = "formell_eingereicht"

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
    date_hierarchy = "anfang"

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


# Lesung


@admin.action(description="Mark selected Lesungen as 'Erfolgreich gelesen'")
def mark_lesung_erfolgreich(modeladmin, request, queryset):
    success_count = 0
    failed = []

    for lesung in queryset:
        lesung.status = "E"
        try:
            with transaction.atomic():
                lesung.full_clean()  # validate first
                lesung.save()
            success_count += 1
        except ValidationError as e:
            failed.append(f"{lesung}: {e}")

    if success_count:
        messages.success(
            request, f"{success_count} Lesungen marked as 'Erfolgreich gelesen'."
        )
    if failed:
        messages.error(request, "Failed to update some Lesungen:\n" + "\n".join(failed))


@admin.action(description="Lesungen wurden wegen Sitzungsende vertagt")
def mark_lesung_wegen_ende_vertagt(modeladmin, request, queryset):
    for lesung in queryset:
        lesung.status = "ZV"
        lesung.save()
    messages.success(
        request,
        f"{len(queryset)} Lesungen sind jetzt 'Wegen Ende der Sitzung vertagt'.",
    )


@admin.register(Lesung)
class LesungAdmin(admin.ModelAdmin):
    list_display = ("antrag", "sitzung")
    list_filter = (
        "antrag__legislatur",
        "sitzung__legislatur",
        "dringlichkeit_beantragt",
        "abstimmbar",
    )
    search_fields = ("antrag__titel", "protokolleintraege")
    actions = [mark_lesung_erfolgreich, mark_lesung_wegen_ende_vertagt]

    def get_legislatur(self, obj):
        return obj.antrag.legislatur

    get_legislatur.short_description = "Legislatur"

    # limit Sitzung queryset to match Antrag's Legislatur in admin form
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
