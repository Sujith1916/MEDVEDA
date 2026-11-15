"""
terminology.py
Cross-system terminology lookup module.

Maintains backward compatibility with original prototype mappings while
seamlessly leveraging the official medical knowledge base (knowledge_base.db).
"""

from typing import Any, Dict, List
import knowledge_db

# Initial demonstration mappings for the prototype (preserved for backwards compatibility).
TERMINOLOGY_DATA = [
    {
        "concept": "diabetes",
        "terms": {
            "allopathy": ["Diabetes mellitus"],
            "ayurveda": ["Madhumeha", "Prameha"],
            "homeopathy": ["Diabetes mellitus (ICD-10 E10/E11)"]
        },
        "relationship": "partial_conceptual_overlap (needs clinical verification)",
        "source": "SNOMED CT / NAMASTE SAT / ICD-10"
    }
]


def find_equivalent_terms(source_system: str, source_term: str) -> List[Dict[str, Any]]:
    """
    Finds corresponding or related terms across medical systems.
    First checks demonstration entries, then queries the official knowledge database.
    """
    search_term = source_term.strip().casefold()
    results = []

    # 1. Check in-memory demonstration mappings
    for entry in TERMINOLOGY_DATA:
        terms = entry["terms"]
        source_terms = [t.casefold() for t in terms.get(source_system, [])]

        if search_term == entry["concept"].casefold() or any(search_term in t for t in source_terms):
            matches = {}
            for system, system_terms in terms.items():
                if system != source_system:
                    matches[system] = system_terms

            results.append({
                "concept": entry["concept"],
                "matches": matches,
                "relationship": entry["relationship"],
                "source": entry.get("source") or "Demonstration Dataset"
            })

    # 2. Query official knowledge_base.db if available
    try:
        comparison = knowledge_db.compare_across_systems(search_term)
        all_sys_matches = {}

        for sys_name in ["allopathy", "ayurveda", "homeopathy"]:
            if sys_name == source_system:
                continue
            concepts = comparison.get(sys_name, [])
            term_list = []
            for c in concepts[:3]:
                code_str = f" [{c.get('code')}]" if c.get('code') else ""
                term_list.append(f"{c.get('term')}{code_str}")
            all_sys_matches[sys_name] = term_list

        # If any matches found in the official database and not already in results
        has_any_match = any(len(v) > 0 for v in all_sys_matches.values())
        if has_any_match:
            results.append({
                "concept": f"{source_term} (Official Knowledge Base)",
                "matches": all_sys_matches,
                "relationship": "surface_term_match (not verified as clinically equivalent)",
                "source": "Official Medical Databases (BHTS / NAMASTE / PCIM&H)"
            })
    except Exception as e:
        print("Warning: Could not query knowledge database in find_equivalent_terms:", e)

    return results
