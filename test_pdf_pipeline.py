import os
import unittest
import sys
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

# Add parent path to import utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import pdf_extractor

class TestPDFOCRPipeline(unittest.TestCase):

    def setUp(self):
        self.selectable_pdf_path = "test_selectable.pdf"
        self.scanned_pdf_path = "test_scanned.pdf"
        self.corrupted_pdf_path = "test_corrupted.pdf"
        self.empty_pdf_path = "test_empty.pdf"
        
        # 1. Generate a selectable PDF using ReportLab
        c = canvas.Canvas(self.selectable_pdf_path)
        c.drawString(100, 750, "Patient Name: Robert Smith")
        c.drawString(100, 730, "Facility: Sacred Heart Hospital")
        c.drawString(100, 710, "Diagnosis: Acute Asthma exacerbation")
        c.drawString(100, 690, "Prescribed Albuterol once daily.")
        c.save()

        # 2. Generate a scanned PDF (Image page) using PIL
        img = Image.new('RGB', (800, 1000), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        # Use standard simple font/text for drawing
        d.text((100, 100), "Patient Name: Sarah Jenkins", fill=(0, 0, 0))
        d.text((100, 130), "Facility: Mercy Medical Center", fill=(0, 0, 0))
        d.text((100, 160), "Prescribed Metformin 500 mg.", fill=(0, 0, 0))
        img.save(self.scanned_pdf_path, "PDF", resolution=100.0)

        # 3. Generate a corrupted file (write garbage data)
        with open(self.corrupted_pdf_path, "w") as f:
            f.write("THIS IS NOT A VALID PDF FILE CONTENT")
            
        # 4. Generate an empty file
        with open(self.empty_pdf_path, "wb") as f:
            pass

    def tearDown(self):
        # Clean up files
        for path in [self.selectable_pdf_path, self.scanned_pdf_path, self.corrupted_pdf_path, self.empty_pdf_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    def test_text_cleaning_heuristics(self):
        print("\n--- Testing Text Cleaning Heuristics ---")
        dirty_text = (
            "Patient Name: John Doe\n"
            "Date of Birth: 1980-05-15\n"
            "History: Patient has been suffering\n"
            "from severe cough and chest tightness\n"
            "for the past week.\n"
            "Diagnosis:\n"
            "Acute Bronchitis.\n"
            "Plan:\n"
            "1. Prescribed Albuterol PRN.\n"
            "2. Follow up in one week."
        )
        cleaned = pdf_extractor.clean_extracted_text(dirty_text)
        print(f"Cleaned Text Output:\n{cleaned}\n---")
        
        # Verify line merging worked for the "suffering from severe..." sentence
        self.assertIn("Patient has been suffering from severe cough and chest tightness for the past week.", cleaned)
        # Verify structural blocks remain separated
        self.assertIn("Diagnosis:\nAcute Bronchitis.", cleaned)
        self.assertIn("1. Prescribed Albuterol PRN.", cleaned)

    def test_selectable_pdf_pipeline(self):
        print("\n--- Testing Selectable PDF Route ---")
        # Ensure it is classified as selectable
        is_sel = pdf_extractor.is_selectable_pdf(self.selectable_pdf_path)
        self.assertTrue(is_sel)
        
        # Run extraction
        text, mode = pdf_extractor.process_pdf(self.selectable_pdf_path)
        print(f"Mode: {mode}")
        print(f"Extracted Text:\n{text}")
        
        self.assertEqual(mode, "Direct PDF Text Extraction")
        self.assertIn("Robert Smith", text)
        self.assertIn("Sacred Heart Hospital", text)
        self.assertIn("Acute Asthma exacerbation", text)

    def test_scanned_pdf_pipeline(self):
        print("\n--- Testing Scanned PDF (OCR) Route ---")
        # Ensure it is classified as NOT selectable (since it contains no selectable text characters)
        is_sel = pdf_extractor.is_selectable_pdf(self.scanned_pdf_path)
        self.assertFalse(is_sel)
        
        # Run OCR extraction
        text, mode = pdf_extractor.process_pdf(self.scanned_pdf_path)
        print(f"Mode: {mode}")
        print(f"OCR Extracted Text:\n{text}")
        
        self.assertEqual(mode, "OCR Mode Enabled")
        self.assertIn("Sarah Jenkins", text)
        self.assertIn("Mercy Medical Center", text)
        self.assertIn("Metformin", text)

    def test_error_handling(self):
        print("\n--- Testing Error Handling ---")
        # 1. Corrupted PDF check
        with self.assertRaises(Exception):
            pdf_extractor.process_pdf(self.corrupted_pdf_path)
            
        # 2. Empty PDF check
        with self.assertRaises(ValueError) as context:
            pdf_extractor.process_pdf(self.empty_pdf_path)
        self.assertIn("empty", str(context.exception).lower())

if __name__ == '__main__':
    unittest.main()
