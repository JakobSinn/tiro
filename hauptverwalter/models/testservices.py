from django.test import TestCase
from hauptverwalter.models.organisation import Faden, Schiffchen, Lesung
from hauptverwalter.models.sitzungen import Legislatur, Sitzung
from hauptverwalter.models.tagesordnung import Tagesordnungspunkt
from django.utils.timezone import make_aware
from hauptverwalter.service import (
    get_active_schiffchen,
    get_current_legislature,
    get_current_legislature_nr,
)
from datetime import datetime


class Testaktiveschiffchen(TestCase):
    def setUp(self):
        l1 = Legislatur.objects.create(anfang="2026-01-01", ende="2026-12-31", nummer=1)
        l2 = Legislatur.objects.create(anfang="2027-01-01", ende="2027-12-31", nummer=2)
        f1 = Faden.objects.create(email="1@example.com", kontaktperson="1kontakt")
        Schiffchen.objects.create(legislatur=l1, hauptfaden=f1, erwartete_lesungen=2)
        f2 = Faden.objects.create(email="2@example.com", kontaktperson="2kontakt")
        Schiffchen.objects.create(legislatur=l1, hauptfaden=f2, erwartete_lesungen=2)
        Faden.objects.create(
            email="1.1@example.com", kontaktperson="1.1kontakt", ueberfaden=f1
        )
        f3 = Faden.objects.create(email="3@example.com", kontaktperson="3kontakt")
        Schiffchen.objects.create(legislatur=l2, hauptfaden=f3, erwartete_lesungen=2)
        Sitzung.objects.create(
            legislatur=l1,
            ort="ort",
            anfang=make_aware(datetime(2026, 1, 1, 18)),
            nummer=1,
        )

    def testaktuellelegislatur(self):
        self.assertEqual(get_current_legislature_nr(), 2)
        self.assertEqual(get_current_legislature().nummer, 2)

    def testamanfang_get_active_schiffchen(self):
        rl1 = get_active_schiffchen(Legislatur.objects.get(nummer=1)).values()
        self.assertIn(
            Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="1@example.com")),
            rl1,
        )
        self.assertIn(
            Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="2@example.com")),
            rl1,
        )
        self.assertNotIn(
            Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="3@example.com")),
            rl1,
        )

    def testnachabstimmung_get_active_schiffchen(self):
        s2 = Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="2@example.com"))
        l2 = Lesung.objects.create(schiffchen=s2)
        t1 = Tagesordnungspunkt.objects.create(
            lesung=l2, nummer=5, sitzung=Sitzung.objects.get(nummer=1), ergebnis="A"
        )
        rl1 = get_active_schiffchen(Legislatur.objects.get(nummer=1)).values()

        self.assertIn(
            Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="1@example.com")),
            rl1,
        )
        self.assertNotIn(
            Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="2@example.com")),
            rl1,
        )
        self.assertNotIn(
            Schiffchen.objects.get(hauptfaden=Faden.objects.get(email="3@example.com")),
            rl1,
        )
