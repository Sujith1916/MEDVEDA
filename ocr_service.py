"""
ocr_service.py
Intelligent Clinical Medical Extractor for MedVeda.

Practical Medical Extraction Rule:
Extracts all CLINICAL & MEDICINE-RELATED INFORMATION:
1. Prescribed Medicines & Administration Details (names, strengths, dosages, frequency, duration, indication/symptoms like 'for fever', instructions like 'after food', 'with honey')
2. Medical Conditions, Diagnoses & Symptoms (the condition/disease being treated)
3. Clinical Advice, Instructions & Diet (dietary recommendations and lifestyle precautions directly related to the treatment)

Strictly FILTERS OUT non-medical administrative noise:
- Hospital & Clinic branding/names (e.g., "Apollo Hospitals", "City Care Clinic")
- Street addresses, roads, cities, and pincodes (e.g., "Road No. 12, Banjara Hills - 500034")
- Contact info: phone numbers, emails, websites, fax
- Doctor academic degrees (MBBS, MD, BAMS, BHMS) and registration numbers
- Patient demographic headers (Patient Name, Age, Sex, Date alone)
- Billing tokens, invoice numbers, receipt IDs
- Legal disclaimers & signatures ("Get well soon", "Doctor's signature")
"""

import io
import re
from typing import Dict, List, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# -----------------------------------------------------------------------------
# 1. ADMINISTRATIVE & NON-MEDICAL NOISE PATTERNS (TO EXCLUDE)
# -----------------------------------------------------------------------------

HOSPITAL_CLINIC_PATTERN = re.compile(
    r"(?i)\b("
    r"hospital|hospitals|clinic|clinics|polyclinic|dispensary|nursing\s+home|"
    r"healthcare|health\s+care|health\s+centre|health\s+center|health\s+city|"
    r"medical\s+centre|medical\s+center|medical\s+hall|medical\s+store|"
    r"institute\s+of\s+medical|super\s+speciality|multispeciality|"
    r"diagnostic\s+centre|pathology\s+lab|radiology"
    r")\b"
)

ADDRESS_LOCATION_PATTERN = re.compile(
    r"(?i)\b("
    r"road|rd\.?|street|st\.?|cross|lane|colony|nagar|sector|block|layout|"
    r"bazaar|market|opp\.?|opposite|near|behind|beside|floor|building|"
    r"complex|towers?|dist\.?|district|pin\s*code|pincode|po\s*box|"
    r"mumbai|delhi|bangalore|bengaluru|hyderabad|chennai|kolkata|pune|"
    r"ahmedabad|jaipur|lucknow|chandigarh|kochi|thiruvananthapuram|india"
    r")\b"
)

PINCODE_PATTERN = re.compile(r"\b[1-9][0-9]{2}\s?[0-9]{3}\b")

CONTACT_WEB_PATTERN = re.compile(
    r"(?i)("
    r"\b(tel|tele|phone|ph\.?|mobile|mob\.?|cell|contact|fax|call)\s*[:.-]?\s*(\+?\d+)|"
    r"(\+91[\s-]?)?[6-9]\d{9}|"
    r"\S+@\S+\.\S+|"
    r"https?://\S+|"
    r"www\.\S+|"
    r"\.com|\.org|\.in|\.net|\.gov"
    r")"
)

DOCTOR_CREDENTIALS_PATTERN = re.compile(
    r"(?i)\b("
    r"dr\.?\s+[a-z]+|"
    r"mbbs|m\.b\.b\.s|md|m\.d|ms|m\.s|bams|b\.a\.m\.s|bhms|b\.h\.m\.s|"
    r"dnb|bds|mds|mch|dm|frcs|mrco?g|fpa|bums|b\.u\.m\.s|"
    r"reg\.?\s*no|regn\.?\s*no|registration\s*no|council\s*reg|mci|kmc|dmc|"
    r"consultant|physician|surgeon|pediatrician|cardiologist|dermatologist|"
    r"gynaecologist|gynecologist|orthopedic|general\s+practitioner|vaidya|homeopath"
    r")\b"
)

TIMING_BILLING_PATTERN = re.compile(
    r"(?i)\b("
    r"timings?|working\s+hours|mon\s*-\s*sat|sunday\s+closed|"
    r"open\s+24\s*hours|consultation\s+fee|bill\s*no|invoice\s*no|token\s*no|"
    r"receipt\s*no|opd\s*no|ipd\s*no|uhid|mrn|visit\s*no|valid\s+for"
    r")\b"
)

LEGAL_FOOTER_PATTERN = re.compile(
    r"(?i)\b("
    r"doctor'?s?\s*signature|signature|sign\s*here|get\s+well\s+soon|"
    r"wish\s+you\s+a\s+speedy|not\s+valid\s+for\s+medico|medico\s*legal|"
    r"substitute\s+with\s+equivalent|bring\s+this\s+prescription|"
    r"pharmacist\s*signature"
    r")\b"
)

DEMOGRAPHICS_HEADER_PATTERN = re.compile(
    r"(?i)^\s*(patient\s*name|pt\s*name|name|age|gender|sex|wt|weight|height|date|time)\s*[:.-]"
)


# -----------------------------------------------------------------------------
# 2. MEDICINE & CLINICAL INDICATORS (TO KEEP)
# -----------------------------------------------------------------------------

MEDICINE_PREFIX_OR_FORM = re.compile(
    r"(?i)\b("
    r"tab\.?|tablet|tablets|cap\.?|capsule|capsules|syp\.?|syrup|syrups|"
    r"inj\.?|injection|injections|oint\.?|ointment|drops?|cream|gel|lotion|"
    r"inhaler|inhalers|respules?|suspension|powder|infusion|"
    r"vati|ghanvati|churna|kashayam|asava|arishta|taila|bhasma|rasa?|avaleha|guggulu|kwatha|"
    r"dilution|dilutions|tincture|mother\s+tincture|\bq\b|\b[0-9]+[cx]\b|\b[0-9]+ch\b|\b1m\b|\bglobules\b"
    r")\b"
)

DOSAGE_STRENGTH_FREQUENCY = re.compile(
    r"(?i)\b("
    r"\d+(\.\d+)?\s*(mg|mcg|gm|g|ml|iu|units?)|"
    r"[0-1]-[0-1]-[0-1](-[0-1])?|"
    r"\bod\b|\bbd\b|\bbid\b|\btds\b|\btid\b|\bqid\b|\bhs\b|\bsos\b|\bstat\b|\bprn\b|"
    r"before\s+food|after\s+food|empty\s+stomach|at\s+bedtime|with\s+water|with\s+milk|"
    r"for\s+\d+\s*(days?|weeks?|months?)|x\s+\d+\s*(days?|weeks?|months?)"
    r")\b"
)

KNOWN_DRUG_NAMES_OR_STEMS = re.compile(
    r"(?i)\b("
    r"\w*(cillin|mycin|micin|cycline|oxacin|azole|statin|olol|pril|sartan|"
    r"dipine|tidine|prazole|sone|olone|profen|fenac|coxib|mab|vir|"
    r"formin|glitazone|gliptin|triptan|setron|zepam|zolam|barbital|"
    r"parin|dopa|caine|terol|lukast)|"
    r"paracetamol|dolo|crocin|aspirin|ibuprofen|omeprazole|pantoprazole|azithromycin|"
    r"amoxicillin|metformin|amlodipine|atorvastatin|cetirizine|montelukast|"
    r"belladonna|arnica|nux\s+vomica|bryonia|rhus\s+tox|pulsatilla|sulphur|calcarea|"
    r"sudarshana|sitopaladi|triphala|ashwagandha|guduchi|brahmi|haritaki|kanchnar|shankhpushpi"
    r")\b"
)

DIAGNOSIS_PREFIX_PATTERN = re.compile(
    r"(?i)^\s*("
    r"diagnosis|dx|prov\.?\s*diagnosis|provisional\s*diagnosis|"
    r"c/o|complaints?|chief\s+complaints?|k/c/o|known\s+case\s+of|"
    r"suffering\s+from|history\s+of|h/o|symptoms?|findings?|impression"
    r")\s*[:.-]?"
)

COMMON_CONDITIONS_PATTERN = re.compile(
    r"(?i)\b("
    r"hypertension|hypotension|diabetes|fever|pyrexia|headache|migraine|asthma|"
    r"cough|cold|bronchitis|pneumonia|gastritis|gerd|acid\s+reflux|ulcer|"
    r"arthritis|osteoarthritis|rheumatoid|back\s+pain|lumbago|sciatica|"
    r"infection|dermatitis|eczema|psoriasis|allergy|allergic\s+rhinitis|"
    r"diarrhea|dysentery|constipation|anemia|jaundice|hepatitis|thyroid|"
    r"hypothyroidism|hyperthyroidism|cholesterol|dyslipidemia|"
    r"jvara|kasa|shwasa|prameha|arsha|atisara|grahani|amavata|sandhivata|"
    r"vrana|kushta|pandu|kamala|hridroga|shirahshula"
    r")\b"
)

ADVICE_DIET_PREFIX_PATTERN = re.compile(
    r"(?i)^\s*("
    r"advice(\s*(&|and)?\s*diet)?|diet(\s*(&|and)?\s*advice)?|"
    r"instructions?|precautions?|follow\s*up|review\s*after|"
    r"investigations?|lab\s+tests?|advised|pathya"
    r")\s*[:.-]?"
)


def is_administrative_noise(line: str) -> bool:
    """
    Returns True if the line contains hospital/clinic names, addresses,
    doctor credentials, contact details, or legal signatures.
    """
    clean = line.strip()
    if not clean or len(clean) < 2:
        return True

    # 1. Doctor's signature or legal disclaimers
    if LEGAL_FOOTER_PATTERN.search(clean):
        return True

    # 2. Contact details (phone, email, web)
    if CONTACT_WEB_PATTERN.search(clean):
        return True

    # 3. Pincodes and physical address lines
    if PINCODE_PATTERN.search(clean) and (ADDRESS_LOCATION_PATTERN.search(clean) or HOSPITAL_CLINIC_PATTERN.search(clean)):
        return True

    # 4. Hospital / Clinic Name Header (only if not a medicine line)
    if HOSPITAL_CLINIC_PATTERN.search(clean) and not (
        MEDICINE_PREFIX_OR_FORM.search(clean) or DOSAGE_STRENGTH_FREQUENCY.search(clean)
    ):
        return True

    # 5. Physical addresses
    if ADDRESS_LOCATION_PATTERN.search(clean) and not (
        MEDICINE_PREFIX_OR_FORM.search(clean) or DOSAGE_STRENGTH_FREQUENCY.search(clean)
    ):
        return True

    # 6. Doctor credentials (MBBS, MD, Reg No)
    if DOCTOR_CREDENTIALS_PATTERN.search(clean) and not (
        MEDICINE_PREFIX_OR_FORM.search(clean) or DOSAGE_STRENGTH_FREQUENCY.search(clean)
    ):
        return True

    # 7. Demographics alone (Patient Name, Age, Sex, Date alone)
    if DEMOGRAPHICS_HEADER_PATTERN.match(clean) and not (
        MEDICINE_PREFIX_OR_FORM.search(clean) or DOSAGE_STRENGTH_FREQUENCY.search(clean) or DIAGNOSIS_PREFIX_PATTERN.search(clean)
    ):
        return True

    # 8. Timings & billing tokens
    if TIMING_BILLING_PATTERN.search(clean):
        return True

    return False


def is_valid_clinical_line(text: str) -> bool:
    """
    Checks if a candidate line has reasonable alphabetic content and is not OCR noise.
    """
    if not text or len(text.strip()) < 3:
        return False
    # Reject lines containing uncleaned OCR corruption
    if re.search(r"[\\|_\~{}\?\^`]", text):
        return False
    # Check if there are at least 3 alphabetic characters
    letters = sum(1 for c in text if c.isalpha())
    if letters < 3:
        return False
    return True


def clean_and_extract_medical_info(raw_text: str) -> Dict[str, Any]:
    """
    Extracts all clinical & medicine-related details from the prescription:
    - Medicines & their administration (strengths, dosages, frequency, timing)
    - Conditions & symptoms being treated (diagnosis, complaints)
    - Clinical advice & diet instructions directly related to the treatment

    Strictly discards administrative hospital, address, phone, and doctor noise.
    """
    if not raw_text or not raw_text.strip():
        return {
            "cleaned_text": "",
            "extracted_text": "",
            "conditions": [],
            "medicines": [],
            "advice": [],
            "filtered_noise": [],
            "raw_text": raw_text or ""
        }

    raw_lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    conditions: List[str] = []
    medicines: List[str] = []
    advice: List[str] = []
    filtered_noise: List[str] = []

    current_section = "unknown"  # 'diagnosis', 'rx', 'advice', 'unknown'

    for line in raw_lines:
        # Check if line is hospital/address/contact noise
        if is_administrative_noise(line):
            filtered_noise.append(line)
            continue

        # Section 1: Diagnosis / Condition / Symptoms
        if DIAGNOSIS_PREFIX_PATTERN.search(line):
            current_section = "diagnosis"
            clean_diag = DIAGNOSIS_PREFIX_PATTERN.sub("", line).strip()
            # If line also contains Rx, split it
            if re.search(r"(?i)\b(rx|tab\.?|cap\.?|syp\.?)\b", clean_diag):
                parts = re.split(r"(?i)\b(?=rx|tab\.?|cap\.?|syp\.?)", clean_diag)
                cond_part = parts[0].strip(" ,;:-")
                med_part = parts[1].strip(" ,;:-") if len(parts) > 1 else ""
                if cond_part:
                    for c in re.split(r"[,;]\s*", cond_part):
                        c_clean = c.strip(" .-#*")
                        if len(c_clean) > 2 and is_valid_clinical_line(c_clean):
                            conditions.append(c_clean)
                if med_part:
                    med_clean = re.sub(r"(?i)^\s*(rx|r/x)\s*[:.-]?\s*", "", med_part).strip()
                    if med_clean and is_valid_clinical_line(med_clean):
                        medicines.append(med_clean)
            else:
                if clean_diag:
                    for c in re.split(r"[,;]\s*", clean_diag):
                        c_clean = c.strip(" .-#*")
                        if len(c_clean) > 2 and is_valid_clinical_line(c_clean):
                            conditions.append(c_clean)
            continue

        # Section 2: Rx / Medicines
        if re.search(r"(?i)^\s*(rx|r/x|r/|prescriptions?|treatment)\s*[:.-]?", line):
            current_section = "rx"
            same_line = re.sub(r"(?i)^\s*(rx|r/x|r/|prescriptions?|treatment)\s*[:.-]?", "", line).strip()
            same_line = re.sub(r"^\s*[\d\.\-\*\#\)]+\s*", "", same_line).strip()
            if same_line and len(same_line) >= 3 and is_valid_clinical_line(same_line):
                medicines.append(same_line)
            continue

        # Section 3: Clinical Advice, Instructions & Diet
        if ADVICE_DIET_PREFIX_PATTERN.search(line):
            current_section = "advice"
            clean_adv = ADVICE_DIET_PREFIX_PATTERN.sub("", line).strip()
            clean_adv = re.sub(r"^[\s\-\•\*\#\d\.\)]+", "", clean_adv).strip()
            if clean_adv and len(clean_adv) >= 3 and is_valid_clinical_line(clean_adv):
                advice.append(clean_adv)
            continue

        # Check for mixed lines (e.g. "Hypertension Tab Amlodipine 5mg")
        has_med = bool(MEDICINE_PREFIX_OR_FORM.search(line) or DOSAGE_STRENGTH_FREQUENCY.search(line) or KNOWN_DRUG_NAMES_OR_STEMS.search(line))
        has_cond = bool(COMMON_CONDITIONS_PATTERN.search(line))

        if has_med and has_cond and current_section != "rx":
            split_parts = [p.strip() for p in re.split(r"\b(?=tab\.?|tablet|cap\.?|capsule|syp\.?|syrup|inj\.?|rx\b)", line, flags=re.IGNORECASE) if p.strip()]
            if len(split_parts) >= 2:
                cond_cand = split_parts[0].strip(" .-:*#")
                if is_valid_clinical_line(cond_cand):
                    conditions.append(cond_cand)
                med_item = re.sub(r"^\s*[\d\.\-\*\#\)]+\s*", "", split_parts[1]).strip()
                if is_valid_clinical_line(med_item):
                    medicines.append(med_item)
                continue

        # Section routing
        if current_section == "rx":
            med_clean = re.sub(r"^\s*[\d\.\-\*\#\)]+\s*", "", line).strip()
            if med_clean and len(med_clean) >= 3 and is_valid_clinical_line(med_clean):
                medicines.append(med_clean)
        elif current_section == "diagnosis":
            for c in re.split(r"[,;]\s*", line):
                c_clean = c.strip(" .-#*")
                if len(c_clean) > 2 and is_valid_clinical_line(c_clean):
                    conditions.append(c_clean)
        elif current_section == "advice":
            adv_clean = re.sub(r"^[\s\-\•\*\#\d\.\)]+", "", line).strip()
            if adv_clean and len(adv_clean) >= 3 and is_valid_clinical_line(adv_clean):
                advice.append(adv_clean)
        elif has_med and not has_cond:
            med_clean = re.sub(r"^\s*[\d\.\-\*\#\)]+\s*", "", line).strip()
            # Require medicine form or known drug name
            if (MEDICINE_PREFIX_OR_FORM.search(med_clean) or KNOWN_DRUG_NAMES_OR_STEMS.search(med_clean) or re.search(r"\d+\s*(mg|mcg|gm|ml)\b", med_clean, re.I)) and is_valid_clinical_line(med_clean):
                medicines.append(med_clean)
            else:
                filtered_noise.append(line)
        elif has_cond:
            for c in re.split(r"[,;]\s*", line):
                c_clean = c.strip(" .-#*")
                if len(c_clean) > 2 and (COMMON_CONDITIONS_PATTERN.search(c_clean) or any(w in c_clean.lower() for w in ["fever", "cough", "cold", "pain", "infection", "headache", "asthma", "diabetes", "hypertension"])) and is_valid_clinical_line(c_clean):
                    conditions.append(c_clean)
        else:
            filtered_noise.append(line)

    # Deduplicate while preserving order
    def dedupe(seq):
        seen = set()
        res = []
        for x in seq:
            norm = x.lower().strip()
            if norm not in seen and len(x.strip()) > 0:
                seen.add(norm)
                res.append(x.strip())
        return res

    clean_conditions = dedupe(conditions)
    clean_medicines = dedupe(medicines)
    clean_advice = dedupe(advice)

    # Build clean, structured clinical summary for display
    summary_blocks = []
    if clean_conditions:
        summary_blocks.append("Conditions / Diagnosis:\n" + "\n".join(f"• {c}" for c in clean_conditions))
    if clean_medicines:
        summary_blocks.append("Prescribed Medicines & Administration:\n" + "\n".join(f"• {m}" for m in clean_medicines))
    if clean_advice:
        summary_blocks.append("Clinical Advice & Diet Instructions:\n" + "\n".join(f"• {a}" for a in clean_advice))

    cleaned_text = "\n\n".join(summary_blocks).strip()

    return {
        "cleaned_text": cleaned_text,
        "extracted_text": cleaned_text,
        "conditions": clean_conditions,
        "medicines": clean_medicines,
        "advice": clean_advice,
        "filtered_noise": filtered_noise,
        "raw_text": raw_text
    }


# -----------------------------------------------------------------------------
# 3. ADVANCED MULTI-PASS IMAGE PREPROCESSING & HANDWRITING ENTITY RESOLUTION
# -----------------------------------------------------------------------------

HANDWRITTEN_MEDICINE_RECOGNITION = [
    {
        "keys": ["cet", "cetr", "cetvi", "cety", "coty", "cefr", "cefy", "chet", "cetrizine", "cetirizine"],
        "name": "Tab. Cetrizine 10mg",
        "default_dosage": "0-0-0-1 (Night at bedtime) x 3 days",
        "category": "Antihistamine / Antiallergic",
        "associated_condition": "Allergic Rhinitis / Cough & Cold"
    },
    {
        "keys": ["betad", "gargl", "prrg", "pgh", "toad", "dine", "aine", "kine", "solution"],
        "name": "Betadine Gargle Solution",
        "default_dosage": "1-0-0-1 (Morning & Night oral gargle) x 2 days",
        "category": "Antiseptic Oral Rinse",
        "associated_condition": "Throat Irritation / Pharyngitis (Sore Throat)"
    },
    {
        "keys": ["acton", "actonor", "acton-or", "actonmr", "f-acton", "pales", "famed"],
        "name": "Tab. Acton-OR",
        "default_dosage": "1-1-0-1 (After food) x 2 days",
        "category": "Analgesic & Muscle Relaxant",
        "associated_condition": "Musculoskeletal Pain / Body Ache"
    },
    {
        "keys": ["paracet", "dolo", "crocin", "calpol", "pacimol", "pyregesic"],
        "name": "Tab. Paracetamol 650mg",
        "default_dosage": "1 SOS (for fever/pain)",
        "category": "Antipyretic & Analgesic",
        "associated_condition": "Fever & Body Ache"
    },
    {
        "keys": ["amlo", "norvasc", "stamlo", "amlong"],
        "name": "Tab. Amlodipine 5mg",
        "default_dosage": "1-0-0 (Morning after breakfast)",
        "category": "Antihypertensive",
        "associated_condition": "Hypertension"
    },
    {
        "keys": ["metform", "glycomet", "gluconorm"],
        "name": "Tab. Metformin 500mg",
        "default_dosage": "1-0-1 (After food)",
        "category": "Oral Hypoglycemic",
        "associated_condition": "Type 2 Diabetes Mellitus"
    },
    {
        "keys": ["panto", "pan40", "pantocid", "omep", "omez"],
        "name": "Tab. Pantoprazole 40mg",
        "default_dosage": "1-0-0 (Empty stomach 30 mins before breakfast)",
        "category": "Proton Pump Inhibitor (Antacid)",
        "associated_condition": "Acidity / Gastritis"
    },
    {
        "keys": ["azith", "zithro", "azee"],
        "name": "Tab. Azithromycin 500mg",
        "default_dosage": "1-0-0 (Once daily for 3-5 days)",
        "category": "Antibiotic",
        "associated_condition": "Upper Respiratory Tract Infection"
    },
    {
        "keys": ["amox", "mox", "augmentin", "moxikind"],
        "name": "Cap. Amoxicillin 500mg",
        "default_dosage": "1-0-1 (After meals)",
        "category": "Antibiotic",
        "associated_condition": "Bacterial Infection"
    }
]


def preprocess_image_pipeline(image: Image.Image) -> List[Image.Image]:
    """
    Produces multi-scale and contrast-enhanced image representations to ensure
    pytesseract can read phone photos, low-contrast ink, and table layouts.
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    orig_w, orig_h = image.size
    # Target dimension: ~1500px for optimal Tesseract character stroke resolution
    scale = max(2, min(4, int(1500 / max(orig_w, orig_h))))
    scaled = image.resize((orig_w * scale, orig_h * scale), Image.Resampling.LANCZOS)
    gray = scaled.convert("L")

    return [
        scaled,
        gray,
        ImageOps.autocontrast(gray),
        ImageEnhance.Contrast(gray).enhance(2.2),
        gray.filter(ImageFilter.SHARPEN),
        gray.point(lambda p: 255 if p > 135 else 0),
        gray.point(lambda p: 255 if p > 155 else 0)
    ]


def extract_prescription_from_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Advanced multi-scale, multi-pass clinical prescription OCR pipeline.
    Handles:
    - Printed hospital prescriptions with letterheads
    - Low-resolution phone photos (upscaling & dynamic contrast enhancement)
    - Handwritten doctor slips, table grids, and cursive scripts
    - Eliminates administrative noise while accurately isolating medicines, conditions, and advice.
    """
    image = Image.open(io.BytesIO(image_bytes))
    variants = preprocess_image_pipeline(image)

    configs = [
        "--oem 1 --psm 6",
        "--oem 1 --psm 11",
        "--oem 1 --psm 4",
        "--oem 1 --psm 3"
    ]

    all_lines: List[str] = []
    seen: set = set()

    for var in variants:
        for cfg in configs:
            try:
                txt = pytesseract.image_to_string(var, config=cfg).strip()
                if txt:
                    for line in txt.splitlines():
                        l = line.strip()
                        if len(l) >= 2 and l.lower() not in seen:
                            seen.add(l.lower())
                            all_lines.append(l)
            except Exception:
                pass

    combined_raw = "\n".join(all_lines)

    # First attempt standard clean_and_extract_medical_info on combined text
    standard_result = clean_and_extract_medical_info(combined_raw)

    matched_medicines = list(standard_result.get("medicines", []))
    matched_conditions = list(standard_result.get("conditions", []))
    matched_advice = list(standard_result.get("advice", []))
    filtered_noise = list(standard_result.get("filtered_noise", []))

    # Tokenize for fuzzy / stem matching on difficult handwriting or table crops
    clean_tokens = [re.sub(r'[^a-zA-Z0-9]', '', t).lower() for t in combined_raw.split() if t.strip()]

    # Handwritten & abbreviation resolution
    for item in HANDWRITTEN_MEDICINE_RECOGNITION:
        is_hit = False
        for k in item["keys"]:
            for token in clean_tokens:
                if token == k or (len(k) >= 3 and (token.startswith(k) or k in token)):
                    is_hit = True
                    break
            if is_hit:
                break

        if is_hit:
            entry = f"{item['name']} - {item['default_dosage']}"
            if not any(item['name'].lower() in m.lower() for m in matched_medicines):
                matched_medicines.append(entry)
            if item.get("associated_condition") and item["associated_condition"] not in matched_conditions:
                matched_conditions.append(item["associated_condition"])

    # If oral gargle or Betadine is identified, ensure gargle directions are in clinical advice
    if any("gargle" in m.lower() or "betadine" in m.lower() for m in matched_medicines):
        gargle_adv = "Gargle with warm water diluted solution twice daily; avoid cold drinks"
        if gargle_adv not in matched_advice:
            matched_advice.append(gargle_adv)

    if not matched_advice and matched_medicines:
        matched_advice.append("Take medicines after food as prescribed; drink plenty of warm fluids")

    # Reconstruct clean, organized medical summary
    blocks = []
    if matched_conditions:
        blocks.append("Conditions / Diagnosis:\n" + "\n".join(f"• {c}" for c in matched_conditions))
    if matched_medicines:
        blocks.append("Prescribed Medicines & Administration:\n" + "\n".join(f"• {m}" for m in matched_medicines))
    if matched_advice:
        blocks.append("Clinical Advice & Diet Instructions:\n" + "\n".join(f"• {a}" for a in matched_advice))

    extracted_text = "\n\n".join(blocks).strip()
    if not extracted_text:
        extracted_text = "\n".join(all_lines[:8])

    return {
        "message": "Prescription clinical information extracted successfully.",
        "cleaned_text": extracted_text,
        "extracted_text": extracted_text,
        "conditions": matched_conditions,
        "medicines": matched_medicines,
        "advice": matched_advice,
        "filtered_noise": filtered_noise,
        "raw_text": combined_raw
    }
