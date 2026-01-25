from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.utils import timezone
from django.http import HttpResponse
from django_weasyprint import WeasyTemplateResponseMixin
from docxtpl import DocxTemplate
import io

from .models import Antrag, Unterantrag, Sitzung, Legislatur, Lesung  # noqa: F401
from .forms import BaseAntragForm
from .helper import buildTOPs


def get_current_legislature():
    nummer = Legislatur.objects.order_by("-nummer").first().nummer
    if not nummer:
        return 1
    else:
        return nummer


class AntragLeiterView(TemplateView):
    template_name = "hauptverwalter/antragsleitung.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["aktuelle_legislatur"] = get_current_legislature()
        return context


class BaseAntragView(CreateView):
    model = Antrag
    form_class = BaseAntragForm
    template_name = "hauptverwalter/antrag_form_basic.html"


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
        context["antraege_zahl"] = Antrag.objects.filter(status="B").count()
        context["aktuelle_legislatur"] = get_current_legislature()
        return context


class AntragListView(ListView):
    model = Antrag
    context_object_name = "antraege"
    template_name = "antrag_list.html"

    def get_queryset(self):
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        qs = Antrag.objects.filter(legislatur__nummer=legislatur_nummer).order_by(
            "-nummer"
        )

        # --- Filtering logic ---
        status = self.request.GET.get("status")
        typ = self.request.GET.get("typ")

        if status:
            qs = qs.filter(status=status)
        if typ:
            qs = qs.filter(typ=typ)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        context["legislatur"] = get_object_or_404(Legislatur, nummer=legislatur_nummer)

        # Preserve current filters for template use
        context["current_status"] = self.request.GET.get("status", "")
        context["current_type"] = self.request.GET.get("type", "")

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
        antrag = self.get_object()
        context["antrag"] = antrag
        context["unterantraege"] = Unterantrag.objects.filter(
            hauptantrag=antrag
        ).order_by("nummer")
        context["lesungen"] = Lesung.objects.filter(antrag=antrag).order_by(
            "sitzung__nummer"
        )
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
            # Default lookup by primary key
            return get_object_or_404(queryset, pk=pk)

        if legislatur_nummer and nummer:
            # Lookup by composite key
            return get_object_or_404(
                queryset, legislatur__nummer=legislatur_nummer, nummer=nummer
            )

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
            # Lookup by composite key
            return get_object_or_404(queryset, nummer=nummer)

        # If neither lookup works, raise the normal error
        return get_object_or_404(queryset, pk=None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Order related Lesungen
        context["lesungen"] = self.object.lesung_set.order_by(
            "prio", "antrag__formell_eingereicht"
        )

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

        sitzung = self.object

        context.update(
            {
                "sitzung": sitzung,
                "bloecke": buildTOPs(sitzung),
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

        # Query all lesungen belonging to this Sitzung
        lesungen = (
            Lesung.objects.filter(sitzung=sitzung)
            .select_related("antrag")
            .order_by("priority", "antrag__formell_eingereicht")
        )

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
