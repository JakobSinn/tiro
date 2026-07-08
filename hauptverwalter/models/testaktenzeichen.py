from django.test import TestCase
from hauptverwalter.models.organisation import Faden, Schiffchen
from hauptverwalter.models.sitzungen import Legislatur
from hauptverwalter.service import count_unterfaeden


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


class TestCountUnterfaeden(TestCase):
    def setUp(self):
        self.l1 = Legislatur.objects.create(
            anfang="2026-01-01", ende="2026-12-31", nummer=1
        )
        self.root = Faden.objects.create(email="root@example.com", kontaktperson="root")
        Schiffchen.objects.create(
            legislatur=self.l1, hauptfaden=self.root, erwartete_lesungen=2
        )

    def test_none_counts_as_zero(self):
        self.assertEqual(count_unterfaeden(None), 0)

    def test_leaf_faden_counts_as_zero(self):
        self.assertEqual(count_unterfaeden(self.root), 0)

    def test_counts_all_direct_and_nested_unterfaeden(self):
        child_1 = Faden.objects.create(
            email="child-1@example.com", kontaktperson="child-1", ueberfaden=self.root
        )
        child_2 = Faden.objects.create(
            email="child-2@example.com", kontaktperson="child-2", ueberfaden=self.root
        )
        grandchild = Faden.objects.create(
            email="grandchild@example.com",
            kontaktperson="grandchild",
            ueberfaden=child_1,
        )

        self.assertEqual(count_unterfaeden(self.root), 3)
        self.assertEqual(count_unterfaeden(child_1), 1)
        self.assertEqual(count_unterfaeden(child_2), 0)
