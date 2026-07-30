import os
import unittest
import preprocessing
import model
from utils.pdf_generator import generate_report_pdf

class TestMedicalNERPipeline(unittest.TestCase):

    def setUp(self):
        self.sample_text = (
            "Patient Name: John Doe. Admitted to Mercy Medical Center. "
            "He has a history of Type 2 Diabetes Mellitus. "
            "Symptom is Fever. Prescribed Metformin 500 mg."
        )
        self.test_upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        os.makedirs(self.test_upload_dir, exist_ok=True)
        self.output_pdf_path = os.path.join(self.test_upload_dir, 'test_clinical_report.pdf')

    def test_preprocessing(self):
        print("\n--- Testing Preprocessing ---")
        preproc = preprocessing.preprocess_report(self.sample_text)
        self.assertIsNotNone(preproc)
        self.assertIn("cleaned_text", preproc)
        self.assertIn("sentences", preproc)
        self.assertGreater(len(preproc["sentences"]), 0)
        print(f"Sentences: {preproc['sentences']}")
        print(f"Tokens in Sentence 1: {preproc['tokens_per_sentence'][0]}")

    def test_fallback_entity_extraction(self):
        print("\n--- Testing Entity Extraction (Fallback) ---")
        entities = model.extract_entities_fallback(self.sample_text)
        self.assertIsNotNone(entities)
        self.assertGreater(len(entities), 0)
        
        # Verify specific items
        found_categories = [ent["entity"] for ent in entities]
        print(f"Entities found: {entities}")
        self.assertIn("Patient Name", found_categories)
        self.assertIn("Hospital", found_categories)
        self.assertIn("Disease", found_categories)
        self.assertIn("Medicine", found_categories)
        self.assertIn("Dosage", found_categories)

    def test_pdf_report_generation(self):
        print("\n--- Testing PDF Report Generation ---")
        if os.path.exists(self.output_pdf_path):
            os.remove(self.output_pdf_path)

        # Build mock data structured for the PDF utility
        mock_data = {
            "text": "Patient Name: John Doe. Admitted to Mercy Medical Center. Diagnosed with Type 2 Diabetes.",
            "summary": {
                "Patient Name": ["John Doe"],
                "Hospital": ["Mercy Medical Center"],
                "Disease": ["Type 2 Diabetes"],
                "Medicine": ["Metformin"],
                "Symptoms": ["Fever"],
                "Dosage": ["500 mg"],
                "Procedure": ["Electrocardiogram"]
            },
            "entities": [
                {"word": "John Doe", "entity": "Patient Name", "score": 0.95},
                {"word": "Mercy Medical Center", "entity": "Hospital", "score": 0.95},
                {"word": "Type 2 Diabetes", "entity": "Disease", "score": 0.95}
            ]
        }

        generate_report_pdf(self.output_pdf_path, mock_data)
        self.assertTrue(os.path.exists(self.output_pdf_path))
        print(f"PDF generated successfully at: {self.output_pdf_path}")

        # Cleanup
        if os.path.exists(self.output_pdf_path):
            os.remove(self.output_pdf_path)

if __name__ == '__main__':
    unittest.main()
