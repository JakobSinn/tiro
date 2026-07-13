from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, get_list_or_404
from hauptverwalter.models import sitzungen, dokumente
from hauptverwalter.service import get_faden_from_aktenzeichen, get_schiffchen
from django.http import Http404


class EineSitzungView(DetailView):
    model = sitzungen.Sitzung

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        return context


class AZView(DetailView):
    template = "hauptverwalter/antrag_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        suchzeichen = self.kwargs["input"]
        suchlegislatur = get_object_or_404(
            sitzungen.Legislatur, nummer=suchzeichen.split("/")[0]
        )
        faden = get_faden_from_aktenzeichen(suchzeichen.split("/")[1], suchlegislatur)
        if (not faden) or (not faden.vorlage):
            raise Http404("Zu diesem Aktenzeichen konnte nichts gefunden werden")
        context["hauptversion"] = faden.vorlage
        context["versionen"] = get_list_or_404(
            dokumente.Vorlage.objects.filter(faden=faden)
            .exclude(zeigen=False)
            .exclude(geheim=True)
            .order_by("eingereicht_organisatorisch")
        )
        if not get_schiffchen(faden):
            raise Http404(
                "Die Daten zu diesem Aktenzeichen sind noch nicht vollständig, bitte wende dich mit dem Aktenzeichen an Präsidium oder IT-Referat"
            )
        else:
            context["schiffchen"] = get_schiffchen(faden)


class IndexView(DetailView):
    pass
