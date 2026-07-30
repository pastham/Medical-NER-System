import os
import uuid
import json
import logging
from flask import Flask, request, render_template, redirect, url_for, send_file, abort, flash
from pypdf import PdfReader

# Import project modules
import preprocessing
import model
from utils.pdf_generator import generate_report_pdf
import utils.pdf_extractor as pdf_extractor

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "clinical_ner_secret_key"

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Standard categories we expect
TARGET_CATEGORIES = ["Patient Name", "Disease", "Medicine", "Symptoms", "Dosage", "Procedure", "Hospital"]

def generate_structured_summary_text(summary_dict: dict) -> str:
    """
    Formulates a formatted structured summary in a clinical report style.
    Example:
    Patient:
    John Doe
    
    Disease:
    Type 2 Diabetes Mellitus
    """
    report_lines = []
    
    # We display each category and list the entities
    for cat in TARGET_CATEGORIES:
        entities = summary_dict.get(cat, [])
        report_lines.append(f"{cat}:")
        if entities:
            for item in entities:
                report_lines.append(f"  - {item}")
        else:
            report_lines.append("  - None detected")
        report_lines.append("") # blank line
        
    return "\n".join(report_lines).strip()

def highlight_clinical_text(text: str, entities: list) -> str:
    """
    Applies color-coded HTML spans to the clinical text.
    Sorts entities in descending order of start index to insert HTML markers without shifting indices.
    """
    # Sort from end of string to start
    sorted_entities = sorted(entities, key=lambda x: x['start'], reverse=True)
    
    highlighted = text
    for ent in sorted_entities:
        start = ent['start']
        end = ent['end']
        word = ent['word']
        cat = ent['entity']
        score = ent.get('score', 1.0)
        
        # Build colored marker span
        span = f'<span class="entity-highlight" data-entity="{cat}" title="Confidence: {score*100:.1f}%">{word}</span>'
        
        # Insert tag into string slice
        highlighted = highlighted[:start] + span + highlighted[end:]
        
    return highlighted

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_text():
    clinical_text = request.form.get('clinical_text', '').strip()
    if not clinical_text:
        return redirect(url_for('index'))
        
    try:
        # 1. Run Text Preprocessing pipeline
        preproc_data = preprocessing.preprocess_report(clinical_text)
        cleaned_text = preproc_data["cleaned_text"]
        
        # 2. Run Named Entity Recognition using Transformer
        entities = model.extract_entities_transformer(cleaned_text)
        
        # 3. Create Entity Summary dictionary (group by category and de-duplicate)
        summary = {cat: [] for cat in TARGET_CATEGORIES}
        for ent in entities:
            cat = ent['entity']
            word = ent['word'].strip()
            # De-duplicate entries within the same card for visual neatness
            if word and word not in summary[cat]:
                summary[cat].append(word)
                
        # 4. Generate structured report string
        structured_report_text = generate_structured_summary_text(summary)
        
        # 5. Extract metrics for the execution trace
        flat_tokens = [tok for sent in preproc_data["tokens_per_sentence"] for tok in sent]
        preproc_metrics = {
            "original_len": len(clinical_text),
            "cleaned_len": len(cleaned_text),
            "sentences_count": len(preproc_data["sentences"]),
            "sentences_samples": preproc_data["sentences"][:5],  # sample first 5 sentences
            "tokens_count": len(flat_tokens),
            "tokens_sample": flat_tokens[:35]  # sample first 35 tokens
        }
        
        # 6. Save report data to JSON database
        report_id = str(uuid.uuid4())
        report_data = {
            "id": report_id,
            "original_text": clinical_text,
            "cleaned_text": cleaned_text,
            "entities": entities,
            "summary": summary,
            "structured_report": structured_report_text,
            "preproc_metrics": preproc_metrics
        }
        
        json_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_id}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=4, ensure_ascii=False)
            
        return redirect(url_for('view_result', report_id=report_id))
        
    except Exception as e:
        logger.error(f"Error analyzing text: {e}")
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def analyze_pdf():
    if 'pdf_file' not in request.files:
        return redirect(url_for('index'))
        
    file = request.files['pdf_file']
    if file.filename == '':
        return redirect(url_for('index'))
        
    if file and file.filename.lower().endswith('.pdf'):
        try:
            # Save file temporarily to extract text
            temp_filename = f"{uuid.uuid4()}_{file.filename}"
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
            file.save(temp_filepath)
            
            # Extract plain text from PDF using OCR pipeline
            try:
                extracted_text, pdf_mode = pdf_extractor.process_pdf(temp_filepath)
            except ValueError as ve:
                logger.warning(f"Validation error handling PDF: {ve}")
                flash(str(ve), "error")
                return redirect(url_for('index'))
            except Exception as e:
                logger.error(f"Error executing OCR pipeline: {e}")
                flash("Uploaded PDF is corrupted or invalid. Please check the file.", "error")
                return redirect(url_for('index'))
            finally:
                # Clean up temp upload PDF file
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                
            # Reuse the text analysis pipeline
            preproc_data = preprocessing.preprocess_report(extracted_text)
            cleaned_text = preproc_data["cleaned_text"]
            entities = model.extract_entities_transformer(cleaned_text)
            
            summary = {cat: [] for cat in TARGET_CATEGORIES}
            for ent in entities:
                cat = ent['entity']
                word = ent['word'].strip()
                if word and word not in summary[cat]:
                    summary[cat].append(word)
                    
            structured_report_text = generate_structured_summary_text(summary)
            
            flat_tokens = [tok for sent in preproc_data["tokens_per_sentence"] for tok in sent]
            preproc_metrics = {
                "original_len": len(extracted_text),
                "cleaned_len": len(cleaned_text),
                "sentences_count": len(preproc_data["sentences"]),
                "sentences_samples": preproc_data["sentences"][:5],
                "tokens_count": len(flat_tokens),
                "tokens_sample": flat_tokens[:35]
            }
            
            report_id = str(uuid.uuid4())
            report_data = {
                "id": report_id,
                "original_text": extracted_text,
                "cleaned_text": cleaned_text,
                "entities": entities,
                "summary": summary,
                "structured_report": structured_report_text,
                "preproc_metrics": preproc_metrics,
                "pdf_mode": pdf_mode
            }
            
            json_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_id}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=4, ensure_ascii=False)
                
            return redirect(url_for('view_result', report_id=report_id))
            
        except Exception as e:
            logger.error(f"Error handling PDF upload: {e}")
            flash("An unexpected error occurred during PDF processing.", "error")
            return redirect(url_for('index'))
            
    else:
        flash("Unsupported clinical report format. Please upload a valid PDF.", "error")
        return redirect(url_for('index'))

@app.route('/result/<report_id>')
def view_result(report_id):
    json_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_id}.json")
    if not os.path.exists(json_path):
        return abort(404)
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        # Highlight entities inside the preprocessed/cleaned text
        highlighted = highlight_clinical_text(
            report_data["cleaned_text"], 
            report_data["entities"]
        )
        
        return render_template(
            'result.html',
            report_id=report_id,
            highlighted_text=highlighted,
            summary=report_data["summary"],
            structured_report=report_data["structured_report"],
            preproc_metrics=report_data["preproc_metrics"],
            pdf_mode=report_data.get("pdf_mode")
        )
    except Exception as e:
        logger.error(f"Error loading result dashboard: {e}")
        return redirect(url_for('index'))

@app.route('/download/<report_id>')
def download_pdf(report_id):
    json_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_id}.json")
    if not os.path.exists(json_path):
        return abort(404)
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
            
        # Format dataset for pdf generator
        pdf_input = {
            "text": report_data["cleaned_text"],
            "summary": report_data["summary"],
            "entities": report_data["entities"]
        }
        
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_id}_report.pdf")
        
        # Generate report lab PDF
        generate_report_pdf(pdf_path, pdf_input)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"MedicalNER_Report_{report_id[:8]}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        logger.error(f"Error compiling PDF: {e}")
        return abort(500)

if __name__ == '__main__':
    # Initialize pipelines on startup (CPU/lazy loading handles downloads automatically)
    logger.info("Initializing Flask server. Hugging Face models will lazy-load on first analysis.")
    app.run(host='0.0.0.0', port=5000, debug=True)