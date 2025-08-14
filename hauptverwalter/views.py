from django.shortcuts import get_object_or_404
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from .models import Antrag, Unterantrag, Sitzung, Legislatur, Lesung  # noqa: F401


class SitzungListView(ListView):
    model = Sitzung
    context_object_name = "sitzungen"

    def get_queryset(self):
        # Expecting legislatur_nummer in URL kwargs
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        return Sitzung.objects.filter(legislatur__nummer=legislatur_nummer).order_by(
            "nummer"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        legislatur_nummer = self.kwargs.get("legislatur_nummer")
        context["legislatur"] = get_object_or_404(Legislatur, nummer=legislatur_nummer)
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
