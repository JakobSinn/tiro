from django.test import TestCase
from hauptverwalter.models.organisation import Faden, Schiffchen, Lesung
from hauptverwalter.models.sitzungen import Legislatur, Sitzung
from hauptverwalter.models.tagesordnung import Tagesordnungspunkt
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware
from datetime import datetime


class Testaktiveschiffchen(TestCase):
    def setUp(self):
        l1 = Legislatur.objects.create(anfang="2026-01-01", ende="2026-12-31", nummer=1)
        f1 = Faden.objects.create(email="1@example.com", kontaktperson="1kontakt")
        Schiffchen.objects.create(legislatur=l1, hauptfaden=f1, erwartete_lesungen=2)
        Sitzung.objects.create(
            legislatur=l1,
            ort="ort",
            anfang=make_aware(datetime(2026, 1, 1, 18)),
            nummer=1,
        )
        Lesung.objects.create(
            schiffchen=Schiffchen.objects.get(hauptfaden=f1),
        )

    def testwennkeinelesungbrauchtmanuellentitel(self):
        with self.assertRaises(ValidationError):
            Tagesordnungspunkt.objects.create(
                sitzung=Sitzung.objects.get(nummer=1)
            ).full_clean()
        t1 = Tagesordnungspunkt.objects.create(
            sitzung=Sitzung.objects.get(nummer=1), manueller_titel="Hallo"
        ).full_clean()
        t2 = Tagesordnungspunkt.objects.create(
            sitzung=Sitzung.objects.get(nummer=1),
            lesung=Lesung.objects.all().first(),
        ).full_clean()
        t3 = Tagesordnungspunkt.objects.create(
            sitzung=Sitzung.objects.get(nummer=1),
            manueller_titel="Hallo",
        ).full_clean()
