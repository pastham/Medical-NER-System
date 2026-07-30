import os
import sys
import logging
import re

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Hugging Face Transformers and PyTorch
try:
    import torch
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Hugging Face transformers or PyTorch not installed. The system will run in fallback mode.")

# Global references for pipelines
_biomedical_pipeline = None
_deid_pipeline = None

# Model Identifier Strings
BIOMEDICAL_MODEL_NAME = "d4data/biomedical-ner-all"
DEID_MODEL_NAME = "obi/deid_bert_i2b2"

# Entity Mapping from raw transformer output tags to our target UI tags
ENTITY_MAPPING = {
    # Biomedical NER tags
    "Medication": "Medicine",
    "Disease_disorder": "Disease",
    "Sign_symptom": "Symptoms",
    "Dosage": "Dosage",
    "Diagnostic_procedure": "Procedure",
    "Therapeutic_procedure": "Procedure",
    "Clinical_event": "Procedure",
    # De-identification tags
    "PATIENT": "Patient Name",
    "HOSP": "Hospital"
}

# Supported UI tags
TARGET_CATEGORIES = ["Patient Name", "Disease", "Medicine", "Symptoms", "Dosage", "Procedure", "Hospital"]

def load_pipelines():
    """
    Lazy loads the biomedical and de-identification token classification pipelines.
    Returns True if models are successfully loaded, False otherwise.
    """
    global _biomedical_pipeline, _deid_pipeline
    
    if not TRANSFORMERS_AVAILABLE:
        return False
        
    try:
        # Load Biomedical NER model
        if _biomedical_pipeline is None:
            logger.info(f"Loading Biomedical Transformer Model: {BIOMEDICAL_MODEL_NAME}...")
            _biomedical_pipeline = pipeline(
                "token-classification",
                model=BIOMEDICAL_MODEL_NAME,
                aggregation_strategy="simple",
                device=-1  # Force CPU to avoid CUDA memory issues, or automatically detect if CUDA is available
            )
            logger.info("Biomedical Transformer Model loaded successfully.")
            
        # Load De-identification model (for Patient and Hospital names)
        if _deid_pipeline is None:
            logger.info(f"Loading De-identification Model: {DEID_MODEL_NAME}...")
            _deid_pipeline = pipeline(
                "token-classification",
                model=DEID_MODEL_NAME,
                aggregation_strategy="simple",
                device=-1
            )
            logger.info("De-identification Model loaded successfully.")
            
        return True
    except Exception as e:
        logger.error(f"Error loading Transformer models: {e}. Switching to Mock/Fallback Mode.")
        return False

def resolve_overlapping_entities(entities):
    """
    Resolves overlapping spans by keeping the one with higher confidence (score)
    and removes duplicate or overlapping ranges.
    """
    # Sort entities by start position, then by end position descending
    entities = sorted(entities, key=lambda x: (x['start'], -x['end']))
    
    resolved = []
    for current in entities:
        if not resolved:
            resolved.append(current)
            continue
            
        last = resolved[-1]
        # Check if there is an overlap
        if current['start'] < last['end']:
            # Overlap detected! Keep the one with the higher confidence score
            if current['score'] > last['score']:
                resolved[-1] = current
        else:
            resolved.append(current)
            
    return resolved

def extract_entities_transformer(text: str) -> list:
    """
    Runs the clinical text through both Transformer models and merges results.
    """
    if not load_pipelines():
        return extract_entities_fallback(text)
        
    try:
        results = []
        
        # 1. Run Biomedical model
        bio_results = _biomedical_pipeline(text)
        for ent in bio_results:
            raw_group = ent.get("entity_group")
            mapped_type = ENTITY_MAPPING.get(raw_group)
            if mapped_type:
                results.append({
                    "word": ent["word"],
                    "entity": mapped_type,
                    "start": ent["start"],
                    "end": ent["end"],
                    "score": float(ent["score"])
                })
                
        # 2. Run De-identification model
        deid_results = _deid_pipeline(text)
        for ent in deid_results:
            raw_group = ent.get("entity_group")
            mapped_type = ENTITY_MAPPING.get(raw_group)
            if mapped_type:
                results.append({
                    "word": ent["word"],
                    "entity": mapped_type,
                    "start": ent["start"],
                    "end": ent["end"],
                    "score": float(ent["score"])
                })
                
        # 3. Clean up overlapping boundaries
        resolved_results = resolve_overlapping_entities(results)
        return resolved_results
        
    except Exception as e:
        logger.error(f"Inference error using Transformer models: {e}. Falling back.")
        return extract_entities_fallback(text)

def extract_entities_fallback(text: str) -> list:
    """
    Smart clinical fallback regex & lexicon-based NER matcher.
    Ensures that the application operates even without model downloads.
    """
    logger.info("Executing NLP Fallback Mode (Regex & Context Rules).")
    entities = []
    
    # 1. Structured lists of common entities in test datasets / clinical reports
    dictionary = {
        "Patient Name": ["John Doe", "Jane Doe", "John", "Jane", "Alice", "Robert Smith", "Sarah Jenkins", "Michael Johnson", "David Miller"],
        "Hospital": ["General Hospital", "St. Jude Hospital", "Mercy Medical Center", "Mayo Clinic", "Boston Medical", "City Medical Center", "Sacred Heart Hospital"],
        "Disease": [
            "Type 2 Diabetes Mellitus", "Type 2 Diabetes", "Diabetes", "Hypertension", "Coronary Artery Disease", 
            "Asthma", "Pneumonia", "Chronic Obstructive Pulmonary Disease", "COPD", "Myocardial Infarction", 
            "Atrial Fibrillation", "Stroke", "Osteoarthritis", "Depression", "Hyperlipidemia"
        ],
        "Medicine": [
            "Metformin", "Lisinopril", "Atorvastatin", "Albuterol", "Amlodipine", 
            "Aspirin", "Ibuprofen", "Amoxicillin", "Insulin Glargine", "Metoprolol", 
            "Lipitor", "Synthroid", "Gabapentin"
        ],
        "Symptoms": [
            "Fever", "Headache", "Chest pain", "Shortness of breath", "Cough", 
            "Nausea", "Fatigue", "Dizziness", "Abdominal pain", "Joint pain", 
            "Swelling", "Sore throat", "Congestion"
        ],
        "Dosage": [
            "500 mg", "10 mg", "20 mg", "100 mg", "500mg", "10mg", "once daily", "twice daily", "BID", "QD", "PRN"
        ],
        "Procedure": [
            "Electrocardiogram", "ECG", "Chest X-ray", "CT Scan", "Echocardiogram", 
            "Endoscopy", "Colonoscopy", "Blood Draw", "MRI of the Brain", "Appendectomy", "Angioplasty"
        ]
    }
    
    # Simple regex scanner for dictionary terms (case insensitive)
    # To prevent boundary errors, we order by text length (descending)
    found_spans = [] # list of (start, end) to avoid overlapping
    
    for category, terms in dictionary.items():
        for term in sorted(terms, key=len, reverse=True):
            # Escaping the term for regex matching
            escaped_term = re.escape(term)
            pattern = re.compile(rf"\b{escaped_term}\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                start, end = match.start(), match.end()
                
                # Check for overlap
                overlap = False
                for f_start, f_end in found_spans:
                    if (start >= f_start and start < f_end) or (end > f_start and end <= f_end):
                        overlap = True
                        break
                        
                if not overlap:
                    found_spans.append((start, end))
                    entities.append({
                        "word": text[start:end],
                        "entity": category,
                        "start": start,
                        "end": end,
                        "score": 0.95  # Simulated high confidence for exact match
                    })
                    
    # 2. Context-based pattern rules for Patient Name, Dosages, Hospitals
    # Patient name patterns (e.g., Patient: John Doe)
    patient_patterns = [
        r"(?:Patient Name|Patient|Name)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:Mr\.|Ms\.|Mrs\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    ]
    for pattern in patient_patterns:
        for match in re.finditer(pattern, text):
            name_val = match.group(1).strip()
            start, end = match.start(1), match.end(1)
            # Check overlap
            overlap = False
            for f_start, f_end in found_spans:
                if (start >= f_start and start < f_end) or (end > f_start and end <= f_end):
                    overlap = True
                    break
            if not overlap:
                found_spans.append((start, end))
                entities.append({
                    "word": name_val,
                    "entity": "Patient Name",
                    "start": start,
                    "end": end,
                    "score": 0.88
                })
                
    # Hospital patterns (e.g., admitted to Boston General Hospital)
    hospital_patterns = [
        r"(?:admitted to|at|transferred to)\s+([A-Z][a-zA-Z\s]+(?:Hospital|Medical Center|Clinic))"
    ]
    for pattern in hospital_patterns:
        for match in re.finditer(pattern, text):
            hosp_val = match.group(1).strip()
            start, end = match.start(1), match.end(1)
            overlap = False
            for f_start, f_end in found_spans:
                if (start >= f_start and start < f_end) or (end > f_start and end <= f_end):
                    overlap = True
                    break
            if not overlap:
                found_spans.append((start, end))
                entities.append({
                    "word": hosp_val,
                    "entity": "Hospital",
                    "start": start,
                    "end": end,
                    "score": 0.85
                })

    # Sort results by character start index
    entities = sorted(entities, key=lambda x: x["start"])
    return entities