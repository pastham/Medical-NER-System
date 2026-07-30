# An Intelligent Medical Named Entity Recognition System for Clinical Text Analysis

A final-year B.Tech engineering research project in the domain of **Speech and Natural Language Processing (SNLP)**.

This application is an intelligent clinical tool that automatically processes raw, unstructured clinical notes (history, consults, discharge summaries) and extracts key clinical concepts using state-of-the-art Deep Learning Transformer models. It presents findings on a modern, dark-themed medical dashboard, generates structured summaries, and provides PDF analysis reports for doctors.

---

## Key Features

1. **Hybrid Deep Learning Named Entity Recognition**: Uses pre-trained Transformer architectures (`d4data/biomedical-ner-all` and `obi/deid_bert_i2b2`) to extract:
   - **Patient Name** & **Hospital Name** (via clinical de-identification/HIPAA models)
   - **Disease**, **Medicine**, **Symptoms**, **Dosages**, and **Procedures** (via clinical token classification models)
   - No simple keywords or rules are used for entity extraction.
2. **Clinical PDF Text Extraction & OCR Pipeline**: Supports both selectable text PDFs and scanned document PDFs:
   - **Selectable Text**: Extracted directly using `pdfplumber` or `pypdf`.
   - **Scanned/Image PDFs**: Automatically converted to images using `pdf2image` and processed using `EasyOCR` (with a fallback to `Tesseract OCR` if needed).
   - **Zero-Dependency Page Rendering**: Falls back to `pypdfium2` to convert pages to images if Poppler binaries are not in the system path.
3. **Advanced Text Preprocessing**: Leverages `spaCy` to run whitespace cleaning, sentence segmentation (preventing BERT token limitation truncation), and token tracking.
4. **Voice Dictation (Future Scope)**: Implements HTML5 Speech Recognition API for hands-free clinical transcription with real-time waveform animation.
5. **Interactive Highlight Display**: Highlights extracted concepts in the narrative with category-specific colors and tooltips.
6. **EHR Structured Summary**: Auto-generates standard clinical EHR summaries that can be copied with one click.
7. **ReportLab PDF Downloads**: Generates formal clinical PDF reports with structured metadata, narrative transcripts, and complete token-classification matrices.

---

## Directory Structure

```
MedicalNERProject/
│── app.py                 # Flask MVC Controller (routes, PDF text parser)
│── model.py               # Hugging Face Transformer inference & fallback
│── preprocessing.py       # spaCy text cleaner & sentence segmenter
│── requirements.txt       # Python package dependencies
│── README.md              # Documentation and Guide
├── dataset/               # Placeholder folder for clinical evaluation sets
├── uploads/               # Temporary storage folder for generated reports
├── templates/
│   ├── index.html         # Main dashboard and microphone input UI
│   └── result.html        # Interactive highlighting page
├── static/
│   ├── css/
│   │   └── styles.css     # Premium medical CSS layout
│   └── js/
│       └── main.js        # Web Speech, upload zones, UI control
├── models/                # Local cache folder for model parameters
└── utils/
    └── pdf_generator.py   # ReportLab PDF building script
```

---

## Tech Stack

- **Backend**: Python 3.8+, Flask
- **Deep Learning / NLP**: Hugging Face Transformers, PyTorch, spaCy
- **PDF & OCR Utils**: PyPDF, pdfplumber, pdf2image, pypdfium2, EasyOCR, pytesseract, ReportLab
- **Frontend**: HTML5, Vanilla CSS3 (Dark medical layout), JavaScript

---

## Advanced OCR Pipeline Setup (Optional)

For scanned PDF reports and prescriptions, the application uses **EasyOCR** and **pdf2image**. While the system has built-in zero-dependency fallbacks, installing external binaries yields optimal results:

1. **Poppler** (for PDF-to-Image conversion):
   - **Windows**: Download poppler for Windows, extract it, and add the `bin/` folder to your system Environment Variables (PATH).
   - **macOS**: Install via Homebrew: `brew install poppler`.
   - **Linux**: Install via package manager: `sudo apt-get install poppler-utils`.
   - *Note: If Poppler is missing, the system will automatically fall back to `pypdfium2` which runs out-of-the-box.*

2. **Tesseract OCR** (for Tesseract OCR fallback):
   - **Windows**: Download and install the Windows Tesseract installer from UB Mannheim, and add the installation folder (usually `C:\Program Files\Tesseract-OCR`) to your system PATH.
   - **macOS**: Install via Homebrew: `brew install tesseract`.
   - **Linux**: Install via package manager: `sudo apt-get install tesseract-ocr`.

---

## Setup & Installation

### Step 1: Navigate to the Workspace
Ensure you are inside the `MedicalNERProject` directory.

### Step 2: Set up a Python Virtual Environment
We recommend using a virtual environment (`venv`) to keep dependencies isolated:
```bash
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate   # On macOS/Linux
```

### Step 3: Install Required Packages
Install all libraries listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```
*Note: Installing PyTorch and Hugging Face Transformers may take a few minutes depending on your internet connection speed.*

### Step 4: Download spaCy Language Pipeline
Pre-download the spaCy English pipeline:
```bash
python -m spacy download en_core_web_sm
```
*(The `preprocessing.py` script will attempt to download this automatically on first run if it is missing, but pre-installing is recommended).*

### Step 5: Start the Flask Application
Run the Flask controller:
```bash
python app.py
```

Open your browser and navigate to: `http://localhost:5000`

---

## Usage Guide

1. **Dashboard Interface**:
   - On the homepage, choose between typing text directly or uploading a PDF file.
   - You can also use the **Microphone** button to dictate clinical notes in real-time.
2. **Demo Quick Start**:
   - Click on any of the **Sample Clinical Reports** buttons (Diabetes, Cardiac, Asthma) at the bottom. This will pre-fill the text area with realistic clinical reports for immediate evaluation.
3. **Running the Analysis**:
   - Click **Run Medical NER Analysis**. On the first run, the system will download the Model parameters (~700MB total) from the Hugging Face Hub. A loading spinner will keep you updated.
   - Submitting will redirect you to the visual results board.
4. **Exporting**:
   - Scroll to the bottom of the results board and click **Download PDF Document** to save a formal medical report to your downloads folder.
