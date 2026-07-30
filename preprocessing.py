import re
import spacy
import subprocess
import sys

# Global variable to hold spaCy model
_nlp = None

def get_spacy_model():
    """
    Loads and returns the spaCy 'en_core_web_sm' model.
    If the model is not installed, it attempts to download it automatically.
    """
    global _nlp
    if _nlp is not None:
        return _nlp

    try:
        # Disable unused components for efficiency during preprocessing
        _nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
        # Re-enable sentencizer/parser if needed for sentence segmentation
        _nlp.enable_pipe("senter") if "senter" in _nlp.pipe_names else _nlp.add_pipe("sentencizer")
        return _nlp
    except OSError:
        print("spaCy model 'en_core_web_sm' not found. Attempting to download...", file=sys.stderr)
        try:
            subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
            _nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
            if "senter" in _nlp.pipe_names:
                _nlp.enable_pipe("senter")
            else:
                _nlp.add_pipe("sentencizer")
            return _nlp
        except Exception as e:
            print(f"Failed to download spaCy model: {e}. Falling back to simple regex-based preprocessing.", file=sys.stderr)
            return None

def clean_whitespace(text: str) -> str:
    """
    Cleans clinical report text by removing redundant whitespaces, tabs,
    and trailing line breaks while keeping paragraphs recognizable.
    """
    if not text:
        return ""
    # Standardize newline characters
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Clean multiple spaces (excluding newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Clean multiple vertical spaces
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def segment_sentences(text: str) -> list:
    """
    Segments the preprocessed clinical text into sentences.
    Falls back to regex-based segmentation if spaCy is unavailable.
    """
    nlp = get_spacy_model()
    if nlp:
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    
    # Fallback sentence splitter using common punctuation boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def tokenize_text(text: str) -> list:
    """
    Tokenizes the text into list of word/punctuation tokens.
    Falls back to a simple split tokenizer if spaCy is unavailable.
    """
    nlp = get_spacy_model()
    if nlp:
        doc = nlp(text)
        return [token.text for token in doc]
    
    # Fallback word-level tokenizer
    return re.findall(r'\w+|[^\w\s]', text)

def preprocess_report(text: str) -> dict:
    """
    Combines cleaning, segmentation, and tokenization steps into a single preprocessing pipeline.
    Returns a dictionary structure suitable for MVC model input.
    """
    cleaned = clean_whitespace(text)
    sentences = segment_sentences(cleaned)
    segmented_tokens = [tokenize_text(sent) for sent in sentences]
    
    return {
        "original_text": text,
        "cleaned_text": cleaned,
        "sentences": sentences,
        "tokens_per_sentence": segmented_tokens
    }
