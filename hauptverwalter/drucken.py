from datetime import datetime
from fpdf import FPDF
from django.contrib.staticfiles import finders
from .models

def bericht_status_pdf(Antrag):
    """
    Generiert ein PDF, dass insbesondere in der Sitzung benutzt werden soll und einen spezifischen Antrag zeigt"""
    # PDF generieren
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_page()
    # Kopfzeile des Zettels mit Logo, Datum, und zu Abstimmungsgegenstand
    pdf.set_font("helvetica", "B", 22)
    pdf.set_y(12)
    pdf.multi_cell(w=80, text="Antrag " + Antrag.legislatur + "/" + Antrag.nummer, align="C", border=1, padding=5)
    pdf.set_y(40)
    pdf.set_font("helvetica", "", size=16)
    pdf.write_html(
        text="<p style=\"line-height:1.5\"\\>Eingereicht: " + Antrag.formell_eingereicht)
    
    return bytes(pdf.output())
