"""
knowledge_db.py
Database layer for the official medical knowledge base (knowledge_base.db).

This module manages the SQLite schema, connections, and query operations
for the three official medical systems:
  - Allopathy (SNOMED CT / BHTS)
  - Ayurveda (NAMASTE Standardized Ayurvedic Terminology)
  - Homeopathy (NAMASTE ICD-10 & PCIM&H Homoeopathic Pharmacopoeia of India)

This database is strictly separated from user medical records (medical_records.db).
"""

import json
import sqlite3
from typing import Any, Dict, List, Optional

KNOWLEDGE_DB_NAME = "knowledge_base.db"


def get_connection() -> sqlite3.Connection:
    """Creates a connection to knowledge_base.db with dictionary-like row access."""
    connection = sqlite3.connect(KNOWLEDGE_DB_NAME)
    connection.row_factory = sqlite3.Row
    # Enable foreign key constraint support in SQLite
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def initialize_knowledge_database():
    """
    Initializes the database schema if tables do not already exist.
    Creates tables: sources, medical_concepts, synonyms, concept_mappings.
    """
    connection = get_connection()
    cursor = connection.cursor()

    # 1. Sources table - records the official metadata, publisher, and licensing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_key TEXT UNIQUE NOT NULL,
            source_name TEXT NOT NULL,
            publisher TEXT NOT NULL,
            source_url TEXT NOT NULL,
            version TEXT,
            retrieval_date TEXT NOT NULL,
            license_information TEXT NOT NULL
        );
    """)

    # 2. Medical concepts table - core concepts across Allopathy, Ayurveda, Homeopathy
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_concepts (
            concept_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER NOT NULL,
            medical_system TEXT NOT NULL,
            concept_type TEXT NOT NULL,
            term TEXT NOT NULL,
            code TEXT NOT NULL,
            definition TEXT,
            extra_data TEXT,
            FOREIGN KEY (source_id) REFERENCES sources (source_id) ON DELETE CASCADE,
            UNIQUE(source_id, code, term)
        );
    """)

    # 3. Synonyms table - alternative terms, translations, IAST transliterations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synonyms (
            synonym_id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_id INTEGER NOT NULL,
            synonym TEXT NOT NULL,
            synonym_type TEXT DEFAULT 'synonym',
            FOREIGN KEY (concept_id) REFERENCES medical_concepts (concept_id) ON DELETE CASCADE,
            UNIQUE(concept_id, synonym)
        );
    """)

    # 4. Concept mappings table - relationships across systems (explicit evidence only)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_mappings (
            mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_id_1 INTEGER NOT NULL,
            concept_id_2 INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,
            evidence_source TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'unverified',
            notes TEXT,
            FOREIGN KEY (concept_id_1) REFERENCES medical_concepts (concept_id) ON DELETE CASCADE,
            FOREIGN KEY (concept_id_2) REFERENCES medical_concepts (concept_id) ON DELETE CASCADE
        );
    """)

    # Create indexes for fast case-insensitive search
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_concepts_term
        ON medical_concepts(term COLLATE NOCASE);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_concepts_code
        ON medical_concepts(code COLLATE NOCASE);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_concepts_system
        ON medical_concepts(medical_system);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_synonyms_synonym
        ON synonyms(synonym COLLATE NOCASE);
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_synonyms_concept
        ON synonyms(concept_id);
    """)

    connection.commit()
    connection.close()


def upsert_source(
    source_key: str,
    source_name: str,
    publisher: str,
    source_url: str,
    version: Optional[str],
    retrieval_date: str,
    license_information: str
) -> int:
    """Inserts or updates a medical knowledge source and returns its source_id."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO sources (
            source_key, source_name, publisher, source_url,
            version, retrieval_date, license_information
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_key) DO UPDATE SET
            source_name = excluded.source_name,
            publisher = excluded.publisher,
            source_url = excluded.source_url,
            version = excluded.version,
            retrieval_date = excluded.retrieval_date,
            license_information = excluded.license_information;
    """, (
        source_key, source_name, publisher, source_url,
        version, retrieval_date, license_information
    ))

    cursor.execute("SELECT source_id FROM sources WHERE source_key = ?", (source_key,))
    row = cursor.fetchone()
    source_id = row["source_id"]

    connection.commit()
    connection.close()
    return source_id


def insert_concept(
    source_id: int,
    medical_system: str,
    concept_type: str,
    term: str,
    code: str,
    definition: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> int:
    """
    Inserts a medical concept.
    Returns the concept_id (new or existing).
    """
    connection = get_connection()
    cursor = connection.cursor()

    extra_json = json.dumps(extra_data) if extra_data else None

    cursor.execute("""
        INSERT OR IGNORE INTO medical_concepts (
            source_id, medical_system, concept_type,
            term, code, definition, extra_data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        source_id, medical_system.lower(), concept_type,
        term.strip(), code.strip(), definition, extra_json
    ))

    cursor.execute("""
        SELECT concept_id FROM medical_concepts
        WHERE source_id = ? AND code = ? AND term = ?;
    """, (source_id, code.strip(), term.strip()))
    row = cursor.fetchone()
    concept_id = row["concept_id"]

    connection.commit()
    connection.close()
    return concept_id


def insert_synonym(concept_id: int, synonym: str, synonym_type: str = "synonym") -> Optional[int]:
    """Inserts a synonym for a concept, avoiding duplicates."""
    syn_clean = synonym.strip()
    if not syn_clean:
        return None

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO synonyms (concept_id, synonym, synonym_type)
        VALUES (?, ?, ?);
    """, (concept_id, syn_clean, synonym_type))

    cursor.execute("""
        SELECT synonym_id FROM synonyms
        WHERE concept_id = ? AND synonym = ?;
    """, (concept_id, syn_clean))
    row = cursor.fetchone()
    synonym_id = row["synonym_id"] if row else None

    connection.commit()
    connection.close()
    return synonym_id


def get_all_sources() -> List[Dict[str, Any]]:
    """Retrieves all registered knowledge sources."""
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sources ORDER BY source_id;")
    rows = [dict(r) for r in cursor.fetchall()]
    connection.close()
    return rows


def search_concepts(
    query: str,
    medical_system: Optional[str] = None,
    concept_type: Optional[str] = None,
    limit: int = 40
) -> List[Dict[str, Any]]:
    """
    Searches medical concepts by term, official code, or synonym.
    Supports filtering by medical system ('allopathy', 'ayurveda', 'homeopathy')
    and concept_type ('condition_disease', 'monograph_medicine', etc.).
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    connection = get_connection()
    cursor = connection.cursor()

    sql = """
        SELECT DISTINCT
            c.concept_id,
            c.medical_system,
            c.concept_type,
            c.term,
            c.code,
            c.definition,
            c.extra_data,
            s.source_name,
            s.publisher,
            s.source_url,
            s.license_information
        FROM medical_concepts c
        JOIN sources s ON c.source_id = s.source_id
        LEFT JOIN synonyms syn ON c.concept_id = syn.concept_id
        WHERE (
            c.term LIKE ?
            OR c.code LIKE ?
            OR syn.synonym LIKE ?
        )
    """
    params: List[Any] = [f"%{clean_query}%", f"%{clean_query}%", f"%{clean_query}%"]

    if medical_system:
        sql += " AND c.medical_system = ?"
        params.append(medical_system.lower())

    if concept_type:
        sql += " AND c.concept_type = ?"
        params.append(concept_type)

    sql += " ORDER BY (c.term = ?) DESC, (c.code = ?) DESC, LENGTH(c.term) ASC LIMIT ?"
    params.extend([clean_query, clean_query, limit])

    cursor.execute(sql, params)
    rows = cursor.fetchall()

    results = []
    for r in rows:
        item = dict(r)
        if item.get("extra_data"):
            try:
                item["extra_data"] = json.loads(item["extra_data"])
            except Exception:
                pass
        
        # Attach synonyms for this concept
        cursor.execute(
            "SELECT synonym, synonym_type FROM synonyms WHERE concept_id = ?",
            (item["concept_id"],)
        )
        item["synonyms"] = [dict(s) for s in cursor.fetchall()]
        results.append(item)

    connection.close()
    return results


def get_concept_details(concept_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves full details for a single concept including synonyms, sources, and mappings."""
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            c.*,
            s.source_name,
            s.publisher,
            s.source_url,
            s.version,
            s.retrieval_date,
            s.license_information
        FROM medical_concepts c
        JOIN sources s ON c.source_id = s.source_id
        WHERE c.concept_id = ?;
    """, (concept_id,))
    row = cursor.fetchone()

    if not row:
        connection.close()
        return None

    concept = dict(row)
    if concept.get("extra_data"):
        try:
            concept["extra_data"] = json.loads(concept["extra_data"])
        except Exception:
            pass

    # Fetch synonyms
    cursor.execute(
        "SELECT synonym, synonym_type FROM synonyms WHERE concept_id = ?",
        (concept_id,)
    )
    concept["synonyms"] = [dict(s) for s in cursor.fetchall()]

    # Fetch mappings
    cursor.execute("""
        SELECT
            m.mapping_id,
            m.relationship_type,
            m.evidence_source,
            m.verification_status,
            m.notes,
            c2.concept_id AS related_concept_id,
            c2.medical_system AS related_system,
            c2.term AS related_term,
            c2.code AS related_code
        FROM concept_mappings m
        JOIN medical_concepts c2 ON (
            CASE
                WHEN m.concept_id_1 = ? THEN m.concept_id_2
                ELSE m.concept_id_1
            END
        ) = c2.concept_id
        WHERE m.concept_id_1 = ? OR m.concept_id_2 = ?;
    """, (concept_id, concept_id, concept_id))
    concept["mappings"] = [dict(m) for m in cursor.fetchall()]

    connection.close()
    return concept


def compare_across_systems(term_or_code: str) -> Dict[str, Any]:
    """
    Searches for a term or code across all 3 medical systems.
    Groups results by system so the user and AI can inspect
    available matches, partial overlaps, and missing entries.
    """
    clean_term = term_or_code.strip()
    if not clean_term:
        return {
            "query": "",
            "allopathy": [],
            "ayurveda": [],
            "homeopathy": [],
            "total_matches": 0,
            "disclaimer": "No term entered."
        }

    results_by_system: Dict[str, List[Dict[str, Any]]] = {
        "allopathy": search_concepts(clean_term, medical_system="allopathy", limit=10),
        "ayurveda": search_concepts(clean_term, medical_system="ayurveda", limit=10),
        "homeopathy": search_concepts(clean_term, medical_system="homeopathy", limit=10)
    }

    total = sum(len(items) for items in results_by_system.values())

    return {
        "query": clean_term,
        "allopathy": results_by_system["allopathy"],
        "ayurveda": results_by_system["ayurveda"],
        "homeopathy": results_by_system["homeopathy"],
        "total_matches": total,
        "disclaimer": (
            "Cross-system comparison is for educational purposes only. "
            "Surface or textual similarities do NOT prove clinical equivalence."
        )
    }
