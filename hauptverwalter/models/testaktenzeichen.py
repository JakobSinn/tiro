from django.test import TestCase
from hauptverwalter.models.organisation import Faden, Schiffchen
from hauptverwalter.models.sitzungen import Legislatur


class Testaktenzeichen(TestCase):
    def setUp(self):
        l1 = Legislatur.objects.create(anfang="2026-01-01", ende="2026-12-31", nummer=1)
        f1 = Faden.objects.create(email="1@example.com", kontaktperson="1kontakt")
        Schiffchen.objects.create(legislatur=l1, hauptfaden=f1, erwartete_lesungen=2)
        f2 = Faden.objects.create(email="2@example.com", kontaktperson="2kontakt")
        Schiffchen.objects.create(legislatur=l1, hauptfaden=f2, erwartete_lesungen=2)
        Faden.objects.create(
            email="1.1@example.com", kontaktperson="1.1kontakt", ueberfaden=f1
        )

    def test_ueberfaden(self):
        f1 = Faden.objects.get(email="1@example.com")
        f2 = Faden.objects.get(kontaktperson="2kontakt")
        f11 = Faden.objects.get(email="1.1@example.com")
        self.assertEqual(f11.ueberfaden, f1)
        self.assertEqual(f1.unterfaeden.first(), f11)
        self.assertIsNone(f1.ueberfaden)
        self.assertIsNone(f2.ueberfaden)
        self.assertIsNone(f11.unterfaeden.first())
        self.assertIsNone(f2.unterfaeden.first())

    def test_az(self):
        f1 = Faden.objects.get(email="1@example.com")
        f2 = Faden.objects.get(kontaktperson="2kontakt")
        f11 = Faden.objects.get(email="1.1@example.com")
        self.assertEqual(f1.aktenzeichen, 1)
        self.assertEqual(f2.aktenzeichen, 2)
        self.assertEqual(f11.aktenzeichen, "1.1")
