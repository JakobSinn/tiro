from django.test import TestCase
from django.core.exceptions import ValidationError
from hauptverwalter.models.dokumente import Vorlage
from hauptverwalter.models.organisation import Faden
from hauptverwalter.service import make_aktuelle_vorlage


class Testaktuellevorlage(TestCase):
    def setUp(self):
        Faden.objects.create(email="1@example.com", kontaktperson="1kontakt")
        Faden.objects.create(email="2@example.com", kontaktperson="2kontakt")
        Vorlage.objects.create(
            titel="VL1", text="VL1_text", faden=Faden.objects.get(email="1@example.com")
        )
        Vorlage.objects.create(
            titel="VL2", text="VL2_text", faden=Faden.objects.get(email="2@example.com")
        )

    def test_setup(self):
        self.assertEqual(
            Vorlage.objects.get(titel="VL1").faden,
            Faden.objects.get(kontaktperson="1kontakt"),
        )
        self.assertEqual(
            Vorlage.objects.get(text="VL2_text").faden,
            Faden.objects.get(email="2@example.com"),
        )

    def test_fadenwechsel(self):
        # VL2 zu Faden 1
        vl2 = Vorlage.objects.get(text="VL2_text")
        vl2.faden = Faden.objects.get(kontaktperson="1kontakt")
        vl2.full_clean()
        vl2.save()
        # VL2 zu aktueller VL machen
        make_aktuelle_vorlage(vl2)
        # Testen
        self.assertEqual(
            Vorlage.objects.get(text="VL2_text"),
            Faden.objects.get(email="1@example.com").aktuelle_vorlage,
        )
        self.assertNotEqual(
            Vorlage.objects.get(titel="VL2"),
            Faden.objects.get(email="2@example.com").aktuelle_vorlage,
        )

    def test_aktuellevorlageinkorrekt(self):
        vl2 = Vorlage.objects.get(text="VL2_text")
        f1 = Faden.objects.get(email="1@example.com")
        f2 = Faden.objects.get(email="2@example.com")
        vl2.faden = f1
        vl2.full_clean()
        vl2.save()
        with self.assertRaises(ValidationError):
            f2.aktuelle_vorlage = vl2
            f2.full_clean()
            f2.save()
        f2.refresh_from_db()
        vl2.refresh_from_db()
        self.assertEqual(vl2.faden, f1)
        self.assertNotEqual(f2.aktuelle_vorlage, vl2)
