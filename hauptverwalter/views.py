from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView

from .models import Antrag, Unterantrag, Sitzung, Legislatur, Lesung  # noqa: F401
from .forms import BaseAntragForm


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

        if nummer:
            # Lookup by composite key
            return get_object_or_404(queryset, nummer=nummer)

        # If neither lookup works, raise the normal error
        return get_object_or_404(queryset, pk=None)
