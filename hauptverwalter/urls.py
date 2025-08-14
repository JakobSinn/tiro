from django.urls import path
from .views import AntragDetailView, SitzungDetailView

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
        "sitzung/<uuid:pk>/",
        SitzungDetailView.as_view(),
        name="sitzung_detail_by_pk",
    ),
    path(
        "sitzung/<int:legislatur_nummer>/<int:nummer>/",
        SitzungDetailView.as_view(),
        name="sitzung_detail_by_nummer",
    ),
]
