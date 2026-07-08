from django.test import TestCase
from django.core.exceptions import ValidationError
from hauptverwalter.models.organisation import Faden, Schiffchen, Lesung
from hauptverwalter.models.sitzungen import Legislatur, Sitzung
from hauptverwalter.models.tagesordnung import Tagesordnungspunkt
from django.utils.timezone import make_aware
from hauptverwalter.service import (
    make_new_top,
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
        Tagesordnungspunkt.objects.create(
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


class TestSitzungValidation(TestCase):
    def setUp(self):
        self.l1 = Legislatur.objects.create(
            anfang="2026-01-01", ende="2026-12-31", nummer=1
        )
        self.l2 = Legislatur.objects.create(
            anfang="2027-01-01", ende="2027-12-31", nummer=2
        )
        self.f1 = Faden.objects.create(email="1@example.com", kontaktperson="1kontakt")
        Schiffchen.objects.create(
            legislatur=self.l1, hauptfaden=self.f1, erwartete_lesungen=2
        )
        self.f2 = Faden.objects.create(email="2@example.com", kontaktperson="2kontakt")
        Schiffchen.objects.create(
            legislatur=self.l1, hauptfaden=self.f2, erwartete_lesungen=2
        )
        Faden.objects.create(
            email="1.1@example.com", kontaktperson="1.1kontakt", ueberfaden=self.f1
        )
        self.f3 = Faden.objects.create(email="3@example.com", kontaktperson="3kontakt")
        Schiffchen.objects.create(
            legislatur=self.l2, hauptfaden=self.f3, erwartete_lesungen=2
        )
        Sitzung.objects.create(
            legislatur=self.l1,
            ort="ort",
            anfang=make_aware(datetime(2026, 1, 1, 18)),
            nummer=1,
        )

    def test_sitzung_within_legislatur_saves(self):
        sitzung = Sitzung(
            legislatur=self.l1,
            ort="ort",
            anfang=make_aware(datetime(2026, 6, 15, 18)),
            nummer=10,
        )

        sitzung.save()

        self.assertEqual(
            Sitzung.objects.get(nummer=10).anfang.date().isoformat(),
            "2026-06-15",
        )

    def test_sitzung_start_before_legislatur_is_rejected(self):
        sitzung = Sitzung(
            legislatur=self.l1,
            ort="ort",
            anfang=make_aware(datetime(2025, 12, 31, 18)),
            nummer=11,
        )

        with self.assertRaises(ValidationError):
            sitzung.save()

    def test_sitzung_end_outside_legislatur_is_allowed_when_start_is_inside(self):
        sitzung = Sitzung(
            legislatur=self.l1,
            ort="ort",
            anfang=make_aware(datetime(2026, 12, 31, 18)),
            ende=make_aware(datetime(2027, 1, 1, 1)),
            nummer=12,
        )

        sitzung.save()

        self.assertEqual(Sitzung.objects.get(nummer=12).ende.year, 2027)

    def testmake_new_top_uses_lowest_eligible_lesung(self):
        schiffchen = Schiffchen.objects.get(
            hauptfaden=Faden.objects.get(email="1@example.com")
        )
        sitzung = Sitzung.objects.get(nummer=1)

        erste_lesung = Lesung.objects.create(schiffchen=schiffchen)
        Tagesordnungspunkt.objects.create(
            lesung=erste_lesung,
            sitzung=sitzung,
            ergebnis="A",
        )
        zweite_lesung = Lesung.objects.create(schiffchen=schiffchen)
        Lesung.objects.create(schiffchen=schiffchen)

        make_new_top(schiffchen, sitzung)

        self.assertEqual(schiffchen.lesungen.count(), 3)
        self.assertEqual(Tagesordnungspunkt.objects.count(), 2)
        self.assertEqual(Tagesordnungspunkt.objects.latest("id").lesung, zweite_lesung)

    def testlesung_nummer_is_one_based_for_same_schiffchen(self):
        schiffchen = Schiffchen.objects.get(
            hauptfaden=Faden.objects.get(email="1@example.com")
        )

        erste_lesung = Lesung.objects.create(schiffchen=schiffchen)
        zweite_lesung = Lesung.objects.create(schiffchen=schiffchen)

        self.assertEqual(erste_lesung.nummer, 1)
        self.assertEqual(zweite_lesung.nummer, 2)

    def testlesung_nummer_ignores_lesungen_of_other_schiffchen(self):
        erstes_schiffchen = Schiffchen.objects.get(
            hauptfaden=Faden.objects.get(email="1@example.com")
        )
        zweites_schiffchen = Schiffchen.objects.get(
            hauptfaden=Faden.objects.get(email="2@example.com")
        )

        fremde_lesung = Lesung.objects.create(schiffchen=zweites_schiffchen)
        eigene_lesung = Lesung.objects.create(schiffchen=erstes_schiffchen)

        self.assertEqual(fremde_lesung.nummer, 1)
        self.assertEqual(eigene_lesung.nummer, 1)
