document.addEventListener('DOMContentLoaded', () => {
    // 1. Tabs Toggling
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
        });
    });

    // 2. Sample Case Loader
    window.loadSampleCase = function(caseType) {
        const textInput = document.getElementById('clinical-text');
        if (!textInput) return;

        let sampleText = "";
        
        if (caseType === 'diabetes') {
            sampleText = 
`Patient Name: John Doe
Date of Birth: 1974-08-12
Admitting Facility: Mercy Medical Center

Chief Complaint:
Patient presents with complaints of persistent fatigue and recurring headache over the past three weeks. He also reports polydipsia and polyuria.

Past Medical History:
History of hyperlipidemia and mild hypertension.

Clinical Assessment & Findings:
Upon examination at Mercy Medical Center, the patient was found to have dry mucous membranes. A random blood draw was performed, showing a glucose level of 280 mg/dL. An Electrocardiogram was conducted which showed normal sinus rhythm.

Diagnosis:
The clinical presentation and lab findings are highly indicative of Type 2 Diabetes Mellitus.

Plan & Treatment:
1. Initiate Metformin 500 mg orally twice daily (BID).
2. Schedule a follow-up consultation in two weeks to review HbA1c results.
3. Patient was educated on diabetic diet and blood sugar monitoring.`;
        } else if (caseType === 'cardiac') {
            sampleText = 
`Patient Name: Robert Smith
Admitting Facility: General Hospital

History of Present Illness:
Mr. Robert Smith is a 62-year-old male who was admitted to General Hospital following an episode of acute chest pain radiating to his left arm, accompanied by severe shortness of breath and diaphoresis.

Diagnostic Procedures:
An immediate Electrocardiogram (ECG) was performed, revealing ST-segment elevation. Subsequently, an urgent Echocardiogram was conducted, confirming anterior wall hypokinesis.

Assessment:
Acute Myocardial Infarction.

Medications & Prescriptions:
1. Aspirin 325 mg chewed immediately.
2. Atorvastatin 80 mg once daily.
3. Metoprolol 25 mg orally twice daily.
4. Schedule coronary Angioplasty as soon as possible.`;
        } else if (caseType === 'asthma') {
            sampleText = 
`Patient Name: Sarah Jenkins
Admitting Facility: St. Jude Hospital

Clinical Notes:
Ms. Sarah Jenkins, a 28-year-old female, presented to the emergency room at St. Jude Hospital complaining of severe cough, wheezing, and chest tightness. She has a known history of chronic asthma.

Physical Examination:
Diffuse bilateral expiratory wheezes were heard on auscultation. A Chest X-ray was ordered, which ruled out active pneumonia.

Assessment:
Acute Asthma exacerbation.

Treatment Plan:
1. Albuterol nebulizer 2.5 mg administered immediately in the clinic.
2. Prescribed Albuterol inhaler (two puffs every 4 hours PRN for wheezing).
3. Prednisolone 40 mg orally once daily for 5 days.
4. Instructed to follow up with pulmonologist in 1 week.`;
        }

        textInput.value = sampleText;
        // Smoothly scroll down to text area
        textInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    // 3. Web Speech-to-Text API
    const recordBtn = document.getElementById('record-btn');
    const voiceStatus = document.getElementById('voice-status');
    const clinicalText = document.getElementById('clinical-text');
    let recognition = null;
    let isRecording = false;
    let waveInterval = null;

    // Check browser compatibility for SpeechRecognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isRecording = true;
            recordBtn.classList.add('recording');
            voiceStatus.textContent = "Listening... Speak now. Click again to stop.";
            startWaveformAnimation();
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (finalTranscript) {
                // Prepend a space if text area already has content and doesn't end with a space
                if (clinicalText.value && !clinicalText.value.endsWith(' ')) {
                    clinicalText.value += ' ';
                }
                clinicalText.value += finalTranscript;
            }
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error: ", event.error);
            voiceStatus.textContent = `Error: ${event.error}. Please try again.`;
            stopRecordingState();
        };

        recognition.onend = () => {
            stopRecordingState();
        };

        recordBtn.addEventListener('click', () => {
            if (isRecording) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
    } else {
        // Fallback for browsers without speech recognition support
        if (recordBtn) {
            recordBtn.style.background = '#6b7280';
            recordBtn.disabled = true;
            voiceStatus.textContent = "Speech-to-Text not supported in this browser.";
        }
    }

    function stopRecordingState() {
        isRecording = false;
        if (recordBtn) recordBtn.classList.remove('recording');
        if (voiceStatus) voiceStatus.textContent = "Voice input standby. Press mic to dictate clinical notes.";
        stopWaveformAnimation();
    }

    // Generate random heights for waveform bars to simulate sound activity
    function startWaveformAnimation() {
        const bars = document.querySelectorAll('.wave-bar');
        waveInterval = setInterval(() => {
            bars.forEach(bar => {
                const height = Math.floor(Math.random() * 26) + 4; // between 4px and 30px
                bar.style.height = `${height}px`;
            });
        }, 100);
    }

    function stopWaveformAnimation() {
        clearInterval(waveInterval);
        const bars = document.querySelectorAll('.wave-bar');
        bars.forEach(bar => {
            bar.style.height = '4px';
        });
    }

    // 4. Drag & Drop PDF upload
    const dragZone = document.getElementById('drag-zone');
    const fileInput = document.getElementById('pdf-file');
    const fileInfo = document.getElementById('file-info');
    const fileNameText = document.getElementById('file-name');
    const fileSizeText = document.getElementById('file-size');

    if (dragZone && fileInput) {
        // Trigger file input click when clicking drag zone
        dragZone.addEventListener('click', (e) => {
            if (e.target !== fileInput && !fileInfo.contains(e.target)) {
                fileInput.click();
            }
        });

        // Visual feedback during dragging
        ['dragenter', 'dragover'].forEach(eventName => {
            dragZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dragZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dragZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dragZone.classList.remove('dragover');
            }, false);
        });

        // Process dropped files
        dragZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                fileInput.files = files;
                updateFileInfo(files[0]);
            }
        });

        // Process selected files
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                updateFileInfo(fileInput.files[0]);
            }
        });
    }

    function updateFileInfo(file) {
        if (file.type !== 'application/pdf') {
            alert('Invalid file format. Please upload a clinical PDF report.');
            fileInput.value = '';
            fileInfo.style.display = 'none';
            return;
        }

        fileNameText.textContent = file.name;
        // Format size to KB/MB
        const sizeInMb = file.size / (1024 * 1024);
        if (sizeInMb < 0.1) {
            fileSizeText.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
        } else {
            fileSizeText.textContent = `(${sizeInMb.toFixed(2)} MB)`;
        }
        fileInfo.style.display = 'flex';
    }

    // 5. Form Submissions and Loading Overlay
    const textForm = document.getElementById('text-form');
    const uploadForm = document.getElementById('upload-form');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');

    if (textForm) {
        textForm.addEventListener('submit', (e) => {
            if (!clinicalText.value.trim()) {
                e.preventDefault();
                alert('Please enter clinical text or click a sample report before analyzing.');
                return;
            }
            showLoading("Analyzing Clinical Notes...", "Running text normalization and BioClinicalBERT Transformer NER pipeline. This may take a minute on initial run to pull model parameters.");
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            if (!fileInput.files.length) {
                e.preventDefault();
                alert('Please select or drop a medical PDF file first.');
                return;
            }
            showLoading("Analyzing Clinical Report...", "Extracting report details, segmenting sentences, and performing Deep Learning Token Classification.");
        });
    }

    function showLoading(title, subtitle) {
        if (loadingOverlay) {
            loadingText.textContent = title;
            const sub = loadingOverlay.querySelector('.loading-subtext');
            if (sub) sub.textContent = subtitle;
            loadingOverlay.style.display = 'flex';
        }
    }
});
