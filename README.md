# MedVeda 🩺🌿
### Cross-System Medical Record Comparison & Official Medical Knowledge Base Platform

## Overview

MedVeda is a web-based medical terminology comparison and medical-record understanding prototype designed to help users comprehend and compare documentation across **Allopathy**, **Ayurveda**, and **Homeopathy**.

The system integrates official, reliable medical terminology databases and pharmacopoeias alongside Tesseract OCR and Open-Source Local AI (Ollama / Llama 3.2) to provide structured cross-system exploration, disease code lookups, and AI-assisted educational comparisons—completely free of commercial closed APIs.

The project is built for **educational and research prototype purposes only**. It does not provide clinical diagnoses, prescribe drug treatments, or declare clinical equivalence between different healthcare systems.

---

## Key Features

- **Isolated Dual Database Architecture:**
  - `medical_records.db`: Stores patient records, prescriptions, condition terms, medicines, patient feedback/comments, and notes.
  - `knowledge_base.db`: Dedicated database containing over **27,000+ official medical concepts**, 47,000+ synonyms, official codes, and source metadata.
- **Three Official Medical Knowledge Sources Integrated:**
  - **Allopathy:** SNOMED CT India National Release (NRCeS BHTS FHIR R4 server).
  - **Ayurveda:** Standardized Ayurvedic Terminology (SAT) from the Ministry of Ayush NAMASTE Portal.
  - **Homeopathy:** Standardized Disease Terminology (ICD-10 Morbidity Codes via NAMASTE) and Official Homoeopathic Pharmacopoeial Single-Drug Monographs (Volumes I–XI via PCIM&H).
- **100% Open-Source Local AI (Ollama):** Powered by local open-source models (such as `llama3.2`, `mistral`, or `meditron`). No closed commercial APIs (no Google Gemini, no OpenAI), zero API key requirements, zero cloud costs, and complete privacy for medical data.
- **Google OAuth Login & User Management:**
  - One-click **Sign in with Google** using Google Identity Services (GIS).
  - During login, the user's name is extracted and set as their **Username**, replacing the previous "Patient Reference" throughout prescription creation, prescription history lookup, and patient records.
- **Patient Feedback & Prescription Comments:** Extra interactive column allowing patients to log their opinions, symptoms relief, or questions for their doctor on any past prescription.
- **Strict Medicine-Only Prescription OCR:**
  - Automated extraction using Tesseract OCR with dedicated medicine-only filtering.
  - Strictly extracts **ONLY the prescribed medicine details** (medicine names, formulations like Tab/Cap/Syp/Vati/Churna, strengths, dosages, and frequencies).
  - Automatically discards all hospital/clinic headers, addresses, doctor credentials, patient demographics, diagnoses, and clinical advice.
  - Automatically populates the extracted medicines into the **Medicine Names** field.
- **Cross-System Terminology Search:** Look up conditions, medicines, or official codes (`SCTID`, `SAT-A`, `ICD-10`, `HPI`) across all three systems.
- **Grounded AI Explanation:** Uses open-source AI with strict guardrails to explain medical concepts in plain language without hallucinating codes, medicines, or clinical equivalence.
- **Patient Record Comparison:** Compares two saved medical records for the same patient to highlight similarities, differences, and patient experience.
- **FastAPI REST API with Interactive Swagger UI:** Self-documenting API available at `/docs`.

---

## Technology Stack

| Component | Technology | Description |
|---|---|---|
| Backend Framework | Python, FastAPI | High-performance asynchronous REST API |
| ASGI Server | Uvicorn | Web server powering FastAPI |
| Databases | SQLite (`medical_records.db` & `knowledge_base.db`) | Two isolated local databases |
| Medical Terminologies | SNOMED CT, SAT, ICD-10, HPI | Official national standards |
| Image OCR | Tesseract OCR & Pillow (`pytesseract`) | Prescription text extraction |
| Open-Source AI Engine | **Ollama REST API** (`http://localhost:11434`) | 100% Open-Source local LLM (`llama3.2`) |
| Data Validation | Pydantic v2 | Request/response schema validation |
| Frontend | Vanilla HTML5, CSS3, JavaScript | Clean, responsive UI with zero external runtime build dependencies |

---

## Project Structure

```text
doctor-vs-vaidya/
├── main.py                     # Main FastAPI application with all REST API endpoints
├── database.py                 # SQLite connection & schema for medical_records.db
├── models.py                   # Pydantic data models (MedicalRecord, TermExplainRequest)
├── terminology.py              # Terminology lookup bridging demo and official database
├── knowledge_db.py             # Database layer for knowledge_base.db (schema & queries)
├── knowledge_service.py        # Business logic for search, comparison, and Gemini integration
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .env                        # Local secrets (GEMINI_API_KEY; never committed)
├── medical_records.db          # User medical records database (preserved)
├── knowledge_base.db          # Official medical knowledge database (separate)
├── data/                       # Official source datasets
│   ├── ayu_sat_table_combined.xlsx   # Official NAMASTE Ayurveda SAT dataset (14,968 rows)
│   ├── icd_10.json                   # Official NAMASTE ICD-10 disease dataset (11,145 rows)
│   ├── pcimh_monographs.json         # Official PCIM&H HPI drug monographs (1,151 rows)
│   └── bhts_snomed_core.json         # Verified SNOMED CT core concepts from NRCeS BHTS
├── importers/                  # Repeatable data import scripts
│   ├── import_ayurveda_namaste.py    # Imports Standardized Ayurvedic Terminology
│   ├── import_homeopathy.py          # Imports ICD-10 diseases and HPI monographs
│   └── import_allopathy_bhts.py      # Imports SNOMED CT clinical concepts
├── tests/                      # Automated test suite
│   └── test_system.py          # Comprehensive 6-suite verification test
└── frontend/
    └── index.html              # Frontend user interface
```

---

## Official Medical Knowledge Sources

### 1. Allopathy – SNOMED CT (NRCeS BHTS)
- **Source:** National Resource Centre for EHR Standards (NRCeS), Centre for Development of Advanced Computing (C-DAC Pune), under the Ministry of Health and Family Welfare (MoHFW), Government of India.
- **Terminology Engine:** Bharat Health Terminology Service (BHTS) HL7 FHIR R4 server (`https://www.nrces.in/bhts/api/v1/ts/fhir/`).
- **Release:** SNOMED CT India National Release (including India AYUSH Extension).
- **Licensing:** Owned by SNOMED International; distributed in India under the national affiliate license.

### 2. Ayurveda – NAMASTE Portal (SAT)
- **Source:** National AYUSH Morbidity and Standardized Terminologies Electronic Portal (NAMASTE), Central Council for Research in Ayurvedic Sciences (CCRAS), Ministry of Ayush, Government of India (`https://namaste.ayush.gov.in/`).
- **Content:** Standardized Ayurvedic Terminology (SAT) containing 14,968 standardized terms with codes (`SAT-A.xxx`), Devanagari script, IAST transliteration, English translation, and definitions.

### 3. Homeopathy – NAMASTE & PCIM&H
- **Disease Terminology:** WHO International Classification of Diseases (ICD-10) adapted by the Ministry of Ayush for morbidity reporting (11,145 disease/symptom terms).
- **Medicine Monographs:** Homoeopathic Pharmacopoeia of India (HPI) official single-drug monographs published across 11 statutory volumes (1971–2025) by the Pharmacopoeia Commission for Indian Medicine & Homoeopathy (PCIM&H), Ministry of Ayush (`https://pcimh.gov.in/`).
- **Separation:** Disease terms (`concept_type = 'condition_disease'`) and drug monographs (`concept_type = 'monograph_medicine'`) are strictly separated in the database.

---

## Database Schema (`knowledge_base.db`)

1. **`sources`**:
   - `source_id` (PK), `source_key` (UK), `source_name`, `publisher`, `source_url`, `version`, `retrieval_date`, `license_information`
2. **`medical_concepts`**:
   - `concept_id` (PK), `source_id` (FK), `medical_system`, `concept_type`, `term`, `code`, `definition`, `extra_data` (JSON)
3. **`synonyms`**:
   - `synonym_id` (PK), `concept_id` (FK), `synonym`, `synonym_type`
4. **`concept_mappings`**:
   - `mapping_id` (PK), `concept_id_1` (FK), `concept_id_2` (FK), `relationship_type`, `evidence_source`, `verification_status`, `notes`

---

## API Endpoints

### Original Endpoints (Preserved)
| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Backend homepage status |
| `GET` | `/api/health` | Backend health check |
| `POST` | `/api/ocr/extract` | Extract text from uploaded prescription photo (Tesseract) |
| `GET` | `/api/terminology/search` | Search terminology mappings (legacy bridged) |
| `POST` | `/api/records` | Create and save a new medical record |
| `GET` | `/api/records` | Retrieve all saved medical records |
| `GET` | `/api/records/{record_id}` | Retrieve one medical record by ID |
| `GET` | `/api/patients/{patient_id}/records` | Retrieve records for a specific patient |
| `GET` | `/api/compare/{record_id_1}/{record_id_2}` | Compare two records belonging to the same patient (via Ollama open-source AI) |
| `PATCH` | `/api/records/{record_id}/comments` | Add or update patient feedback/opinion on a prescription |
| `GET` | `/api/ollama/status` | Check status of the local open-source Ollama AI server and installed models |

### Official Knowledge Base Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/knowledge/sources` | List all 4 registered official medical sources and licensing terms |
| `GET` | `/api/knowledge/search` | Search concepts across Allopathy, Ayurveda, and Homeopathy by term, code, or synonym |
| `GET` | `/api/knowledge/concept/{concept_id}` | Retrieve full concept details, synonyms, mappings, and source metadata |
| `GET` | `/api/knowledge/compare` | Compare a term across all 3 systems, identifying matches, partial overlaps, and gaps |
| `POST` | `/api/knowledge/explain` | Open-source AI educational cross-system explanation via Ollama with safety guardrails |

---

## Running the Application

### 1. Start the Open-Source AI Engine (Ollama)
Download Ollama from [ollama.com](https://ollama.com/download) and run:
```powershell
ollama run llama3.2
```
*Runs completely on your laptop, zero API keys required, 100% private and free.*

### 2. Activate the Virtual Environment
```powershell
# In PowerShell:
.venv\Scripts\Activate.ps1
```

### 3. Verify / Run Data Importers (Idempotent & Repeatable)
```powershell
python importers/import_ayurveda_namaste.py
python importers/import_homeopathy.py
python importers/import_allopathy_bhts.py
```

### 4. Run the Automated Test Suite
```powershell
python tests/test_system.py
```

### 5. Start the FastAPI Backend
```powershell
python -m uvicorn main:app --reload
```

### 6. Open the Web Application
- Open `frontend/index.html` directly in your browser or serve it locally.
- Interactive Swagger API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Backend health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## OCR Workflow

1. User uploads a prescription or EHR image (JPG or PNG).
2. Tesseract OCR processes the image and outputs editable text into the review box.
3. User verifies and corrects any OCR errors.
4. User clicks **"Search Extracted Text in Official Knowledge Base"**.
5. The system queries `knowledge_base.db` across Allopathy, Ayurveda, and Homeopathy.
6. User can click **"Explain with Open-Source AI (Ollama)"** to read a structured educational explanation.

---

## Limitations & Safety Principles

1. **Not a Clinical Decision Support System:** This application is strictly an educational and informational tool.
2. **Textual Match != Clinical Equivalence:** Similar terminology (such as "Diabetes mellitus" and "Madhumeha") reflects distinct pathophysiological frameworks (insulin resistance vs tridoshic metabolic imbalance) and must never be treated as clinical equivalents without formal evidence.
3. **No Automatic Clinical Assertions:** The application and local open-source AI integration never fabricate dosages, medicines, or diagnoses.
4. **Professional Consultation Required:** All medical decisions require review by a licensed healthcare professional.

---

## Academic Information

- **Project:** MedVeda (Cross-System Medical Record Comparison & Official Knowledge Base)
- **Target Use:** Computer Science Engineering & Medical Informatics Prototype
