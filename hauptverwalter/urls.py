from django.urls import path
from hauptverwalter.views.einzelviews import EineSitzungView, IndexView, AZView

urlpatterns = [
    path(
        "sitzung/<int:pk>",
        EineSitzungView.as_view(),
        name="sitzung",
    ),
    path(
        "aktenzeichen/<str:input>",
        AZView.as_view(),
        name="aktenzeichensuche",
    ),
    path(
        "",
        IndexView.as_view(),
        name="index",
    ),
]
