from django.urls import path
from .views import AntragDetailView, SitzungDetailView, SitzungListView, AntragListView

urlpatterns = [
    path(
        "antrag/<uuid:pk>/",
        AntragDetailView.as_view(),
        name="antrag_detail_by_pk",
    ),
    path(
        "antrag/<int:legislatur_nummer>/<int:nummer>/",
        AntragDetailView.as_view(),
        name="antrag_detail_by_nummer",
    ),
    path(
        "antrag/<int:legislatur_nummer>/",
        AntragListView.as_view(),
        name="antrag_by_legislatur",
    ),
    path(
        "sitzung/<int:nummer>/",
        SitzungDetailView.as_view(),
        name="sitzung_detail_by_nummer",
    ),
    path(
        "legislatur/<int:legislatur_nummer>/",
        SitzungListView.as_view(),
        name="legislatur_by_nummer",
    ),
]
