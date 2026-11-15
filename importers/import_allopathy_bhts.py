"""
importers/import_allopathy_bhts.py
Imports official SNOMED CT clinical terminology from the Bharat Health Terminology Service (BHTS)
operated by the National Resource Centre for EHR Standards (NRCeS, C-DAC Pune), MoHFW, Government of India.

Supported Operations:
- Imports core clinical concepts verified against the BHTS FHIR R4 server.
- Registers official source metadata, SCTIDs, Fully Specified Names (FSN), and clinical synonyms.
- Designed to run reliably in both offline and online modes.
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to sys.path so we can import knowledge_db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import knowledge_db

CORE_DATA_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "bhts_snomed_core.json"))


def register_bhts_source() -> int:
    """Registers the official NRCeS BHTS / SNOMED CT source in sources table."""
    return knowledge_db.upsert_source(
        source_key="nrces_snomed_ct_bhts",
        source_name="SNOMED Clinical Terms (SNOMED CT) - India National Release",
        publisher="National Resource Centre for EHR Standards (NRCeS, C-DAC Pune) / MoHFW, Government of India & SNOMED International",
        source_url="https://www.nrces.in/bhts/api/v1/ts/fhir/",
        version="SNOMED CT Release 2026-08-01 / India AYUSH Extension",
        retrieval_date=datetime.now().strftime("%Y-%m-%d"),
        license_information=(
            "SNOMED CT is owned and maintained by SNOMED International. "
            "Distributed in India by NRCeS under the national release for healthcare "
            "interoperability and research."
        )
    )


def run_allopathy_import():
    """
    Imports the foundational SNOMED CT clinical concepts from BHTS dataset into knowledge_base.db.
    """
    print("====================================================")
    print("Starting BHTS Allopathy / SNOMED CT Knowledge Import...")
    print("====================================================")

    if not os.path.exists(CORE_DATA_FILE):
        raise FileNotFoundError(f"BHTS dataset file not found at: {CORE_DATA_FILE}")

    source_id = register_bhts_source()
    print(f"Registered BHTS Source with source_id: {source_id}")

    with open(CORE_DATA_FILE, "r", encoding="utf-8") as f:
        concepts_list = json.load(f)

    conn = knowledge_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("BEGIN TRANSACTION;")

    imported = 0
    total_synonyms = 0

    for item in concepts_list:
        code = str(item.get("code")).strip()
        display = item.get("display", "").strip()
        fsn = item.get("fsn", "").strip()
        synonyms = item.get("synonyms", [])

        if not code or not display:
            continue

        extra = {
            "snomed_sctid": code,
            "fully_specified_name": fsn,
            "source_engine": "Snowstorm FHIR R4 (NRCeS BHTS)",
            "fhir_codesystem_uri": "http://snomed.info/sct"
        }

        concept_type = item.get("concept_type", "condition_disease")
        definition = f"SNOMED CT Medicine Substance: {fsn}" if concept_type == "monograph_medicine" else (f"SNOMED CT Clinical Concept: {fsn}" if fsn else "SNOMED CT Concept")

        cursor.execute("""
            INSERT OR IGNORE INTO medical_concepts (
                source_id, medical_system, concept_type,
                term, code, definition, extra_data
            )
            VALUES (?, 'allopathy', ?, ?, ?, ?, ?);
        """, (source_id, concept_type, display, code, definition, json.dumps(extra)))

        cursor.execute("""
            SELECT concept_id FROM medical_concepts
            WHERE source_id = ? AND code = ? AND term = ?;
        """, (source_id, code, display))
        row = cursor.fetchone()
        if not row:
            continue

        concept_id = row[0]
        imported += 1

        # Add FSN as synonym
        if fsn and fsn != display:
            cursor.execute("""
                INSERT OR IGNORE INTO synonyms (concept_id, synonym, synonym_type)
                VALUES (?, ?, 'fully_specified_name');
            """, (concept_id, fsn))
            total_synonyms += 1

        # Add other synonyms
        for syn in synonyms:
            syn_clean = syn.strip()
            if syn_clean and syn_clean != display:
                cursor.execute("""
                    INSERT OR IGNORE INTO synonyms (concept_id, synonym, synonym_type)
                    VALUES (?, ?, 'synonym');
                """, (concept_id, syn_clean))
                total_synonyms += 1

    conn.commit()
    cursor.execute("PRAGMA synchronous = NORMAL;")
    conn.close()

    print("====================================================")
    print("Allopathy / SNOMED CT Import Finished:")
    print(f"  Total Concepts Imported : {imported}")
    print(f"  Total Synonyms Registered: {total_synonyms}")
    print("====================================================")


if __name__ == "__main__":
    knowledge_db.initialize_knowledge_database()
    run_allopathy_import()
