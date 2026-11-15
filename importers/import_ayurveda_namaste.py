"""
importers/import_ayurveda_namaste.py
Imports official Standardized Ayurvedic Terminology (SAT) from the Ministry of Ayush
NAMASTE portal dataset (ayu_sat_table_combined.xlsx).

Dataset details:
- Source: National AYUSH Morbidity and Standardized Terminologies Electronic Portal (NAMASTE)
- Published by: CCRAS / Ministry of Ayush, Government of India
- Portal: https://namaste.ayush.gov.in/
- Format: OpenXML Spreadsheet (.xlsx)
"""

import json
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime

# Add parent directory to sys.path so we can import knowledge_db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import knowledge_db

EXCEL_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "ayu_sat_table_combined.xlsx"))


def extract_shared_strings(z: zipfile.ZipFile) -> list:
    """Reads the shared strings table from the xlsx zip archive."""
    shared_strings = []
    if "xl/sharedStrings.xml" in z.namelist():
        tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
            text = "".join(t.text for t in si.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") if t.text)
            shared_strings.append(text)
    return shared_strings


def parse_rows(z: zipfile.ZipFile, shared_strings: list):
    """Generator yielding row lists from sheet1.xml."""
    tree = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rows = tree.findall(f".//{ns}row")
    for row in rows:
        row_data = []
        for cell in row.findall(f"{ns}c"):
            cell_type = cell.attrib.get("t")
            v = cell.find(f"{ns}v")
            val = v.text if v is not None else ""
            if cell_type == "s" and val:
                val = shared_strings[int(val)]
            row_data.append(val)
        yield row_data


def run_ayurveda_import(limit: int = None):
    """
    Imports the Standardized Ayurvedic Terminology into knowledge_base.db.
    Uses batch transactions for high performance.
    """
    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(f"Ayurveda dataset file not found at: {EXCEL_FILE}")

    print("====================================================")
    print("Starting NAMASTE Ayurveda Terminology Import...")
    print(f"Dataset path: {EXCEL_FILE}")
    print("====================================================")

    # 1. Register Source in sources table
    source_id = knowledge_db.upsert_source(
        source_key="namaste_ayurveda_sat",
        source_name="Standardized Ayurvedic Terminology (SAT)",
        publisher="Central Council for Research in Ayurvedic Sciences (CCRAS) / Ministry of Ayush, Government of India",
        source_url="https://namaste.ayush.gov.in/admin/assets/excel/namaste/ayu_sat_table_combined.xlsx",
        version="Standardized Ayurvedic Terminology (Combined)",
        retrieval_date=datetime.now().strftime("%Y-%m-%d"),
        license_information=(
            "Official terminology standard published by Ministry of Ayush, Government of India "
            "for national electronic health records and clinical reporting."
        )
    )
    print(f"Registered Ayurveda Source with source_id: {source_id}")

    # 2. Parse Excel archive
    with zipfile.ZipFile(EXCEL_FILE, "r") as z:
        print("Extracting shared strings...")
        shared_strings = extract_shared_strings(z)
        print(f"Loaded {len(shared_strings)} shared strings.")

        row_generator = parse_rows(z, shared_strings)
        header = next(row_generator, None)

        if not header:
            raise ValueError("Empty worksheet: could not find header row.")

        print("Dataset columns:", header)
        col_map = {name: idx for idx, name in enumerate(header)}

        conn = knowledge_db.get_connection()
        cursor = conn.cursor()

        imported_count = 0
        synonyms_count = 0
        errors_count = 0

        # Enable SQLite speed optimizations for bulk batch import
        cursor.execute("PRAGMA synchronous = OFF;")
        cursor.execute("BEGIN TRANSACTION;")

        for row_idx, row in enumerate(row_generator, start=2):
            if limit and imported_count >= limit:
                print(f"Reached specified limit of {limit} records.")
                break

            try:
                def get_val(col_name: str) -> str:
                    idx = col_map.get(col_name)
                    if idx is not None and idx < len(row):
                        return (row[idx] or "").strip()
                    return ""

                term_id = get_val("term_id")
                term_dev = get_val("term_devanagari")
                term_iast = get_val("term_iast")
                w_trans = get_val("w_trans")
                w_def = get_val("w_def")
                wordtree = get_val("wordtree")
                refn = get_val("refn")

                if not term_id and not term_iast and not term_dev:
                    continue

                primary_term = w_trans if w_trans else (term_iast if term_iast else term_dev)
                code = term_id if term_id else f"SAT-{row_idx}"
                definition = w_def if w_def else None

                extra_data = {
                    "term_devanagari": term_dev,
                    "term_iast": term_iast,
                    "english_translation": w_trans,
                    "wordtree": wordtree,
                    "references": refn
                }
                extra_json = json.dumps(extra_data)

                cursor.execute("""
                    INSERT OR IGNORE INTO medical_concepts (
                        source_id, medical_system, concept_type,
                        term, code, definition, extra_data
                    )
                    VALUES (?, 'ayurveda', 'terminology', ?, ?, ?, ?);
                """, (source_id, primary_term, code, definition, extra_json))

                cursor.execute("""
                    SELECT concept_id FROM medical_concepts
                    WHERE source_id = ? AND code = ? AND term = ?;
                """, (source_id, code, primary_term))
                row_match = cursor.fetchone()
                if not row_match:
                    continue
                concept_id = row_match[0]
                imported_count += 1

                # Synonyms
                syns_to_add = []
                if term_dev and term_dev != primary_term:
                    syns_to_add.append((concept_id, term_dev, "devanagari"))
                if term_iast and term_iast != primary_term:
                    syns_to_add.append((concept_id, term_iast, "iast"))
                if w_trans and w_trans != primary_term:
                    syns_to_add.append((concept_id, w_trans, "english_translation"))
                if wordtree and wordtree not in (primary_term, term_iast, term_dev):
                    syns_to_add.append((concept_id, wordtree, "transliteration"))

                for s_cid, s_val, s_type in syns_to_add:
                    cursor.execute("""
                        INSERT OR IGNORE INTO synonyms (concept_id, synonym, synonym_type)
                        VALUES (?, ?, ?);
                    """, (s_cid, s_val, s_type))
                    synonyms_count += 1

                if imported_count % 3000 == 0:
                    conn.commit()
                    cursor.execute("BEGIN TRANSACTION;")
                    print(f"Imported {imported_count} Ayurvedic concepts...")

            except Exception as e:
                errors_count += 1
                if errors_count <= 5:
                    print(f"Error importing row {row_idx}: {e}")

        conn.commit()
        cursor.execute("PRAGMA synchronous = NORMAL;")
        conn.close()

        print("====================================================")
        print("Ayurveda Import Finished:")
        print(f"  Total Concepts Imported : {imported_count}")
        print(f"  Total Synonyms Registered: {synonyms_count}")
        print(f"  Errors Encountered      : {errors_count}")
        print("====================================================")


if __name__ == "__main__":
    knowledge_db.initialize_knowledge_database()
    run_ayurveda_import()
