"""
importers/import_homeopathy.py
Imports official Homeopathy datasets:
1. Disease Terminology: WHO ICD-10 standardized disease coding adapted by Ministry of Ayush (NAMASTE portal).
2. Medicine Monographs: Homoeopathic Pharmacopoeia of India (HPI) official single-drug monographs (Volumes I - XI)
   published by the Pharmacopoeia Commission for Indian Medicine & Homoeopathy (PCIM&H).

Maintains strict separation between disease conditions (concept_type='condition_disease')
and medicine monographs (concept_type='monograph_medicine').
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to sys.path so we can import knowledge_db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import knowledge_db

ICD10_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "icd_10.json"))
PCIMH_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "pcimh_monographs.json"))


def run_homeopathy_import(limit_diseases: int = None, limit_monographs: int = None):
    """
    Imports both disease terminology and medicine monographs into knowledge_base.db.
    """
    print("====================================================")
    print("Starting Homeopathy Knowledge Import...")
    print("====================================================")

    # -----------------------------------------------------------------
    # Part 1: Disease Terminology (NAMASTE ICD-10 adaptation)
    # -----------------------------------------------------------------
    if not os.path.exists(ICD10_FILE):
        print(f"Warning: Disease file not found at {ICD10_FILE}")
        icd_source_id = None
    else:
        icd_source_id = knowledge_db.upsert_source(
            source_key="namaste_homeopathy_icd10",
            source_name="NAMASTE Homeopathy Disease & Morbidity Terminology (ICD-10)",
            publisher="Ministry of Ayush, Government of India / World Health Organization",
            source_url="https://namaste.ayush.gov.in/icd10",
            version="WHO ICD-10 AYUSH Morbidity Edition",
            retrieval_date=datetime.now().strftime("%Y-%m-%d"),
            license_information=(
                "Standardized disease classifications adapted by Ministry of Ayush for "
                "Homeopathy, Yoga, and Naturopathy clinical recording and dual-coding."
            )
        )
        print(f"Registered Homeopathy Disease Source with source_id: {icd_source_id}")

    # -----------------------------------------------------------------
    # Part 2: Medicine Monographs (PCIM&H Homoeopathic Pharmacopoeia)
    # -----------------------------------------------------------------
    if not os.path.exists(PCIMH_FILE):
        print(f"Warning: Monographs file not found at {PCIMH_FILE}")
        hpi_source_id = None
    else:
        hpi_source_id = knowledge_db.upsert_source(
            source_key="pcimh_homeopathy_hpi",
            source_name="Homoeopathic Pharmacopoeia of India (HPI) Official Drug Monographs",
            publisher="Pharmacopoeia Commission for Indian Medicine & Homoeopathy (PCIM&H), Ministry of Ayush, Government of India",
            source_url="https://pcimh.gov.in/homoeopathypharmacopoeialpublications",
            version="Volumes I through XI (1971 - 2025)",
            retrieval_date=datetime.now().strftime("%Y-%m-%d"),
            license_information=(
                "Statutory standards published under the Second Schedule to the Drugs and Cosmetics Act, "
                "1940, Government of India for homoeopathic single-drug medicines."
            )
        )
        print(f"Registered PCIM&H Medicine Source with source_id: {hpi_source_id}")

    conn = knowledge_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("BEGIN TRANSACTION;")

    # -----------------------------------------------------------------
    # Import Diseases
    # -----------------------------------------------------------------
    diseases_count = 0
    disease_synonyms = 0
    if icd_source_id and os.path.exists(ICD10_FILE):
        with open(ICD10_FILE, "r", encoding="utf-8") as f:
            icd_data = json.load(f)

        print(f"Loading {len(icd_data)} disease records from ICD-10...")
        for item in icd_data:
            if limit_diseases and diseases_count >= limit_diseases:
                break

            term = (item.get("word") or "").strip()
            code = (item.get("code") or "").strip()
            if not term or not code:
                continue

            block_title = (item.get("block_title") or "").strip()
            chapt_name = (item.get("chapt_name") or "").strip()
            chapt_roman = (item.get("chapter_no_roman") or "").strip()

            definition_parts = []
            if block_title:
                definition_parts.append(f"Block: {block_title}")
            if chapt_name:
                definition_parts.append(f"Chapter {chapt_roman}: {chapt_name}")
            definition = " | ".join(definition_parts) if definition_parts else None

            extra = {
                "chapter_no": chapt_roman,
                "chapter_name": chapt_name,
                "block_title": block_title
            }

            cursor.execute("""
                INSERT OR IGNORE INTO medical_concepts (
                    source_id, medical_system, concept_type,
                    term, code, definition, extra_data
                )
                VALUES (?, 'homeopathy', 'condition_disease', ?, ?, ?, ?);
            """, (icd_source_id, term, code, definition, json.dumps(extra)))

            cursor.execute("""
                SELECT concept_id FROM medical_concepts
                WHERE source_id = ? AND code = ? AND term = ?;
            """, (icd_source_id, code, term))
            row = cursor.fetchone()
            if row:
                concept_id = row[0]
                diseases_count += 1

                # Add block title as synonym/context
                if block_title and block_title != term:
                    cursor.execute("""
                        INSERT OR IGNORE INTO synonyms (concept_id, synonym, synonym_type)
                        VALUES (?, ?, 'disease_block');
                    """, (concept_id, block_title))
                    disease_synonyms += 1

    conn.commit()
    cursor.execute("BEGIN TRANSACTION;")

    # -----------------------------------------------------------------
    # Import Medicine Monographs
    # -----------------------------------------------------------------
    monographs_count = 0
    monograph_synonyms = 0
    if hpi_source_id and os.path.exists(PCIMH_FILE):
        with open(PCIMH_FILE, "r", encoding="utf-8") as f:
            mono_data = json.load(f)

        print(f"Loading {len(mono_data)} drug monographs from PCIM&H HPI...")
        for item in mono_data:
            if limit_monographs and monographs_count >= limit_monographs:
                break

            drug_name = (item.get("drug_name") or "").strip()
            code = (item.get("code") or "").strip()
            details = (item.get("details") or "").strip()
            vol = item.get("volume", "")
            year = item.get("year", "")

            if not drug_name:
                continue

            definition = f"Homoeopathic Pharmacopoeia of India {vol} ({year}). {details}".strip()

            extra = {
                "volume": vol,
                "publication_year": year,
                "sl_no": item.get("sl_no"),
                "monograph_details": details,
                "source_url": item.get("source_url")
            }

            cursor.execute("""
                INSERT OR IGNORE INTO medical_concepts (
                    source_id, medical_system, concept_type,
                    term, code, definition, extra_data
                )
                VALUES (?, 'homeopathy', 'monograph_medicine', ?, ?, ?, ?);
            """, (hpi_source_id, drug_name, code, definition, json.dumps(extra)))

            cursor.execute("""
                SELECT concept_id FROM medical_concepts
                WHERE source_id = ? AND code = ? AND term = ?;
            """, (hpi_source_id, code, drug_name))
            row = cursor.fetchone()
            if row:
                concept_id = row[0]
                monographs_count += 1

                # If details has a scientific botanical name, add it as synonym
                if details:
                    # extract scientific name before plant part
                    parts = details.split()
                    if len(parts) >= 2 and parts[0][0].isupper():
                        scientific = f"{parts[0]} {parts[1]}"
                        cursor.execute("""
                            INSERT OR IGNORE INTO synonyms (concept_id, synonym, synonym_type)
                            VALUES (?, ?, 'scientific_name');
                        """, (concept_id, scientific))
                        monograph_synonyms += 1

    conn.commit()
    cursor.execute("PRAGMA synchronous = NORMAL;")
    conn.close()

    print("====================================================")
    print("Homeopathy Import Finished:")
    print(f"  Disease Conditions Imported : {diseases_count}")
    print(f"  Medicine Monographs Imported: {monographs_count}")
    print(f"  Total Synonyms Registered   : {disease_synonyms + monograph_synonyms}")
    print("====================================================")


if __name__ == "__main__":
    knowledge_db.initialize_knowledge_database()
    run_homeopathy_import()
