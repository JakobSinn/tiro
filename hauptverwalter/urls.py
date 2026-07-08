from django.urls import path
from hauptverwalter.views.einzelviews import EineSitzungView, IndexView

urlpatterns = [
    path(
        "sitzung/<int:pk>",
        EineSitzungView.as_view(),
        name="sitzung",
    ),
    path(
        "",
        IndexView.as_view(),
        name="index",
    ),
]
