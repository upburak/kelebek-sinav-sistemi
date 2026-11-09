"""Rapor PDF'lerinde Türkçe harflerin doğru basılması.

Gerileme: Türkçe destekleyen sistem yazı tipi bulunamadığında raporlar sessizce
Helvetica'ya dönüyordu. Helvetica WinAnsi kodlamasıyla sınırlı olduğu için
``Çağrı Işık Şükrü İpek`` çıktıya ``Çanrn Innk nükrü npek`` olarak düşüyordu;
öğrenci adları yanlış yazılıyordu.
"""

import io
import unittest

import pdfplumber
from reportlab.pdfbase import pdfmetrics

from kelebek.services import reporting

SAMPLE = "Çağrı Işık Şükrü Ğüneş İpek Öztürk"


def _extract(canvas_font: str) -> str:
    buffer = io.BytesIO()
    pdf = reporting.ReportCanvas(buffer)
    pdf.setFont(canvas_font, 12)
    pdf.drawString(40, 700, SAMPLE)
    pdf.save()
    buffer.seek(0)
    with pdfplumber.open(buffer) as document:
        return (document.pages[0].extract_text() or "").strip()


class ReportFontTests(unittest.TestCase):
    def setUp(self):
        self.candidates = reporting._font_candidates

    def tearDown(self):
        reporting._font_candidates = self.candidates

    def test_turkish_letters_survive_with_a_system_font(self):
        regular, _bold = reporting._register_fonts()
        if regular != reporting.FONT_REGULAR:
            self.skipTest("Bu bilgisayarda Türkçe destekleyen sistem yazı tipi yok.")
        self.assertEqual(_extract(regular), SAMPLE)

    def test_selected_font_actually_contains_turkish_letters(self):
        regular, _bold = reporting._register_fonts()
        if regular != reporting.FONT_REGULAR:
            self.skipTest("Bu bilgisayarda Türkçe destekleyen sistem yazı tipi yok.")
        face = pdfmetrics.getFont(regular).face
        for letter in reporting.TURKISH_LETTERS:
            self.assertTrue(face.charToGlyph.get(ord(letter)), f"{letter} harfi yazı tipinde yok.")

    def test_fallback_transliterates_instead_of_writing_wrong_letters(self):
        reporting._font_candidates = lambda: []
        registered = pdfmetrics.getRegisteredFontNames()
        if reporting.FONT_REGULAR in registered:
            # Yazı tipi kaydı süreç genelinde olduğu için sadeleştirme mantığı doğrudan sınanır.
            self.assertEqual(
                SAMPLE.translate(reporting.ASCII_FALLBACK),
                "Cagri Isik Sukru Gunes Ipek Ozturk",
            )
            return
        self.assertEqual(reporting._register_fonts(), ("Helvetica", "Helvetica-Bold"))
        self.assertEqual(_extract("Helvetica"), "Cagri Isik Sukru Gunes Ipek Ozturk")

    def test_candidate_list_points_at_existing_font_shapes(self):
        for regular, bold in reporting._font_candidates():
            self.assertTrue(regular.lower().endswith((".ttf", ".ttc")), regular)
            self.assertTrue(bold.lower().endswith((".ttf", ".ttc")), bold)

    def test_pdf_text_never_returns_none(self):
        self.assertEqual(reporting.pdf_text(None), "")
        self.assertEqual(reporting.pdf_text(12), "12")


if __name__ == "__main__":
    unittest.main()
