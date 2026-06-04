from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.utils import timezone
from django.http import HttpResponse
from django_weasyprint import WeasyTemplateResponseMixin
from docxtpl import DocxTemplate
import io

from formtools.wizard.views import SessionWizardView

from .models.dokumente import Antrag, SOAntrag, Finanzantrag, Anhang
from .models.sitzungen import Sitzung, Sondersitzung, Legislatur
from .models.organisation import Schiffchen, Faden

from .forms import Step1Form, Step2Form, BasicAntragForm


def get_current_legislature():
    aktuell = Legislatur.objects.order_by("-nummer").first()
    if not aktuell:
        return 1
    return aktuell.nummer


def get_current_legislature_obj():
    return Legislatur.objects.order_by("-nummer").first()


class ListLikeManager:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)

    def count(self):
        return len(self._items)

    def exists(self):
        return bool(self._items)

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)


def _typ_display_for_antrag(antrag):
    if isinstance(antrag, Finanzantrag):
        return "Finanzantrag"
    if isinstance(antrag, SOAntrag):
        return "Satzung / Ordnungsänderung"
    return "Allgemeiner Antrag"


def _status_display_for_antrag(status):
    return {"B": "In Beratung", "A": "Angenommen", "N": "Abgelehnt"}.get(
        status, "In Beratung"
    )


def decorate_antrag(antrag, schiffchen=None):
    schiffchen = (
        schiffchen or Schiffchen.objects.filter(hauptfaden=antrag.faden).first()
    )
    antrag.legislatur = schiffchen.legislatur if schiffchen else None
    antrag.nummer = schiffchen.id if schiffchen else antrag.faden.id
    antrag.status = getattr(antrag, "status", "B")
    antrag.get_status_display = lambda: _status_display_for_antrag(antrag.status)
    antrag.get_typ_display = lambda: _typ_display_for_antrag(antrag)
    antrag.formell_eingereicht = getattr(antrag, "eingereicht_organisatorisch", None)
    antrag.ist_finanzantrag = isinstance(antrag, Finanzantrag)
    antrag.will_orgsatzung_aendern = bool(
        getattr(antrag, "orgsatzungsaenderung", False)
    )
    antrag.beschlussfaehigkeitssicher = getattr(
        antrag, "beschlussfaehigkeitssicher", False
    )
    antrag.anzahl_vertagungen = getattr(antrag, "anzahl_vertagungen", 0)

    unterantraege = []
    if antrag.faden:
        for unterfaden in antrag.faden.unterfaeden.all():
            ua = unterfaden.vorlage
            if ua:
                ua.nummer = unterfaden.id
                ua.formell_eingereicht = getattr(
                    ua, "eingereicht_organisatorisch", None
                )
                ua.get_status_display = lambda: _status_display_for_antrag("B")
                unterantraege.append(ua)
    antrag.unterantrag_set = ListLikeManager(unterantraege)

    lesungen = []
    if schiffchen:
        lesungen = list(schiffchen.lesungen.all())
        for lesung in lesungen:
            lesung.antrag = antrag
            lesung.get_status_display = lambda: ""
    antrag.lesung_set = ListLikeManager(lesungen)

    return antrag


def decorate_sitzung(sitzung):
    now = timezone.now()
    sitzung.is_sondersitzung = isinstance(sitzung, Sondersitzung)
    sitzung.is_future = sitzung.anfang > now
    sitzung.is_running = sitzung.anfang <= now and (
        sitzung.ende is None or sitzung.ende >= now
    )
    sitzung.is_past = bool(sitzung.ende and sitzung.ende < now)
    sitzung.anmerkungen = getattr(sitzung, "anmerkung", None)
    sitzung.lesung_set = ListLikeManager([])
    return sitzung


def create_faden_and_vorlage(cleaned):
    faden = Faden(
        email=cleaned.get("kontaktemail"),
        kontaktperson=cleaned.get("kontaktperson") or "",
    )
    faden.save()

    typ = cleaned.get("typ")
    titel = cleaned.get("titel") or "Antrag"
    if typ == "F":
        vorlage = Finanzantrag(
            faden=faden,
            titel=titel,
            text=cleaned.get("text"),
            begruendung=cleaned.get("begruendung"),
            antragssteller=cleaned.get("antragssteller"),
            antragssumme=cleaned.get("antragssumme"),
            haushaltsposten=cleaned.get("haushaltsposten"),
        )
    elif typ == "S":
        vorlage = SOAntrag(
            faden=faden,
            titel=titel,
            text=cleaned.get("text"),
            begruendung=cleaned.get("begruendung"),
            antragssteller=cleaned.get("antragssteller"),
            orgsatzungsaenderung=cleaned.get("orgsatzungsaenderung") or False,
        )
    else:
        vorlage = Antrag(
            faden=faden,
            titel=titel,
            text=cleaned.get("text"),
            begruendung=cleaned.get("begruendung"),
            antragssteller=cleaned.get("antragssteller"),
        )

    vorlage.save()

    faden.aktuelle_vl = vorlage
    faden.save(update_fields=["aktuelle_vl"])

    if faden.ueberfaden is None:
        legislatur = get_current_legislature_obj()
        schiffchen = Schiffchen(
            hauptfaden=faden,
            legislatur=legislatur,
            erwartete_lesungen=1,
        )
        schiffchen.save()

    anhang = cleaned.get("anhang")
    if anhang:
        Anhang.objects.create(
            faden=faden,
            datei=anhang,
            titel=getattr(anhang, "name", "Anhang"),
        )

    return vorlage


class AntragLeiterView(TemplateView):
    template_name = "hauptverwalter/antragsleitung.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["aktuelle_legislatur"] = get_current_legislature()
        return context


class BaseAntragView(CreateView):
    model = Antrag
    form_class = BasicAntragForm
    template_name = "hauptverwalter/antrag_form_basic.html"

    def form_valid(self, form):
        vorlage = create_faden_and_vorlage(form.cleaned_data)
        return redirect("antrag_detail_by_pk", pk=vorlage.pk)


class AntragWizardView(SessionWizardView):
    """Two-step wizard: step1 collects contact + type, step2 collects Antrag body."""

    form_list = [Step1Form, Step2Form]
    file_storage = None

    def get_template_names(self):
        return ["hauptverwalter/wizard_step.html"]

    def get_form_kwargs(self, step):
        kwargs = super().get_form_kwargs(step)
        # for Step2, forward the selected typ so it can set required fields
        if step == "1":
            # data from step0 (Step1Form) is in storage
            data = self.get_cleaned_data_for_step("0") or {}
            kwargs.update({"selected_typ": data.get("typ")})
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        # expose a human-readable label for the selected typ (from step1) to the template
        step0 = self.get_cleaned_data_for_step("0") or {}
        typ_code = step0.get("typ")
        if typ_code:
            # use Step1Form choices to find label
            try:
                context["selected_typ_label"] = dict(Step1Form.TYPE_CHOICES).get(
                    typ_code
                )
            except Exception:
                context["selected_typ_label"] = typ_code
        else:
            context["selected_typ_label"] = None
        return context

    def done(self, form_list, **kwargs):
        data = {}
        for f in form_list:
            data.update(getattr(f, "cleaned_data", {}) or {})

        vorlage = create_faden_and_vorlage(data)

        return redirect("antrag_detail_by_pk", pk=vorlage.pk)


class SitzungListView(ListView):
    model = Sitzung
    context_object_name = "sitzungen"

    def get_queryset(self):
        # Expecting legislatur_nummer in URL kwargs
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        return Sitzung.objects.filter(legislatur__nummer=legislatur_nummer).order_by(
            "-nummer"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        context["legislatur"] = get_object_or_404(Legislatur, nummer=legislatur_nummer)
        context["sitzungen"] = [decorate_sitzung(s) for s in context["sitzungen"]]
        return context


class IndexView(ListView):
    model = Sitzung
    context_object_name = "sitzungen"
    template_name = "hauptverwalter/index.html"

    def get_queryset(self):
        # Expecting legislatur_nummer in URL kwargs
        return Sitzung.objects.order_by("-nummer")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["antraege_zahl"] = Antrag.objects.count()
        context["aktuelle_legislatur"] = get_current_legislature()
        context["sitzungen"] = [decorate_sitzung(s) for s in context["sitzungen"]]
        return context


class AntragListView(ListView):
    model = Antrag
    context_object_name = "antraege"
    template_name = "antrag_list.html"

    def get_queryset(self):
        return Antrag.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        context["legislatur"] = get_object_or_404(Legislatur, nummer=legislatur_nummer)

        # Preserve current filters for template use
        context["current_status"] = self.request.GET.get("status", "")
        context["current_type"] = self.request.GET.get("type", "")

        schiffchen_qs = Schiffchen.objects.filter(
            legislatur__nummer=legislatur_nummer
        ).select_related("hauptfaden", "legislatur")
        antraege = []
        for schiffchen in schiffchen_qs:
            vorlage = schiffchen.hauptfaden.vorlage
            if isinstance(vorlage, Antrag):
                antraege.append(decorate_antrag(vorlage, schiffchen=schiffchen))
        context["antraege"] = antraege
        return context


class AntragQuittungView(WeasyTemplateResponseMixin, DetailView):
    """
    Erzeugt eine Quittung für einen Antrag, die den aktuellen Datenstand als pdf ausgibt.
    """

    model = Antrag
    template_name = "hauptverwalter/pdf/quittung_antrag.html"
    pdf_filename = None  # will be set dynamically below

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        antrag = decorate_antrag(self.get_object())
        context["antrag"] = antrag
        context["unterantraege"] = antrag.unterantrag_set.all()
        context["lesungen"] = antrag.lesung_set.all()
        context["now"] = timezone.now()
        return context

    def get_pdf_filename(self):
        antrag = self.get_object()
        return f"Quittung_{antrag.legislatur.nummer}_{antrag.nummer}.pdf"

    # Optional: set response headers or PDF metadata
    def get_pdf_response(self, pdf):
        response = super().get_pdf_response(pdf)
        response["Content-Disposition"] = (
            f'inline; filename="{self.get_pdf_filename()}"'
        )
        return response


class AntragDetailView(DetailView):
    model = Antrag
    context_object_name = "antrag"

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()

        pk = self.kwargs.get("pk")
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        nummer = self.kwargs.get("nummer")

        if pk:
            return decorate_antrag(get_object_or_404(queryset, pk=pk))

        if legislatur_nummer and nummer:
            schiffchen = get_object_or_404(
                Schiffchen, legislatur__nummer=legislatur_nummer, id=nummer
            )
            vorlage = schiffchen.hauptfaden.vorlage
            return decorate_antrag(vorlage, schiffchen=schiffchen)

        # If neither lookup works, raise the normal error
        return get_object_or_404(queryset, pk=None)


class SitzungDetailView(DetailView):
    model = Sitzung
    context_object_name = "sitzung"

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        pk = self.kwargs.get("id")
        nummer = self.kwargs.get("nummer")

        if nummer:
            return decorate_sitzung(get_object_or_404(queryset, nummer=nummer))

        if pk:
            return decorate_sitzung(get_object_or_404(queryset, pk=pk))

        # If neither lookup works, raise the normal error
        return get_object_or_404(queryset, pk=None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lesungen"] = self.object.lesung_set.all()
        return context


class SitzungAbstimmungsmatrixView(WeasyTemplateResponseMixin, DetailView):
    """
    Erzeugt eine Abstimmungsmatrix für eine Sitzung als PDF.
    """

    model = Sitzung
    template_name = "hauptverwalter/pdf/abstimmungsmatrix.html"
    pdf_filename = None  # set dynamically

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        return get_object_or_404(
            queryset,
            nummer=self.kwargs.get("nummer"),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sitzung = decorate_sitzung(self.object)
        context.update(
            {
                "sitzung": sitzung,
                "bloecke": [],
                "now": timezone.now(),
            }
        )
        return context

    def get_pdf_filename(self):
        return f"sitzung_{self.object.nummer}_abstimmungsmatrix.pdf"

    def get_pdf_response(self, pdf):
        response = super().get_pdf_response(pdf)
        response["Content-Disposition"] = (
            f'inline; filename="{self.get_pdf_filename()}"'
        )
        return response


class SitzungDocxView(DetailView):
    model = Sitzung
    template_name = None

    docx_template = "docx/sitzung_template.docx"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sitzung = self.object

        lesungen = []

        # Build grouped structure
        grouped = []
        current_priority = None
        priority_block = None

        for l in lesungen:
            if l.priority != current_priority:
                current_priority = l.priority
                priority_block = {"priority": current_priority, "lesungen": []}
                grouped.append(priority_block)
            priority_block["lesungen"].append(l)

        context["sitzung"] = sitzung
        context["lesungen"] = lesungen
        return context

    def render_to_response(self, context, **response_kwargs):
        # Load docx template
        doc = DocxTemplate(self.docx_template)
        doc.render(context)

        # Save into memory buffer
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # Return response
        filename = f"sitzung_{self.object.nummer}.docx"
        response = HttpResponse(
            buffer.getvalue(),
            content_type=(
                "application/"
                "vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
