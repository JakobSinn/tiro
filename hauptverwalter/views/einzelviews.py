from django.views.generic import DetailView
from hauptverwalter.models import sitzungen


class EineSitzungView(DetailView):
    model = sitzungen.Sitzung


class IndexView(DetailView):
    pass
