from django.shortcuts import get_object_or_404
from django.views.generic.detail import DetailView

from .models import Antrag, Unterantrag, Sitzung, Legislatur, Lesung  # noqa: F401


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
