"""
knowledge_service.py
Service layer connecting the official medical knowledge base (knowledge_base.db)
and the open-source Ollama local AI integration (e.g. Llama 3.2).

Features:
- Structured querying across Allopathy, Ayurveda, and Homeopathy.
- Retrieval of official codes, definitions, synonyms, and publisher metadata.
- Cross-system comparison with explicit uncertainty flags.
- Open-source AI-assisted educational explanation with strict safety guardrails.
"""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional
import httpx
import knowledge_db


def list_sources() -> List[Dict[str, Any]]:
    """Returns all registered official medical knowledge sources."""
    return knowledge_db.get_all_sources()


def search_knowledge(
    query: str,
    medical_system: Optional[str] = None,
    concept_type: Optional[str] = None,
    limit: int = 30
) -> Dict[str, Any]:
    """
    Searches across medical systems by term, official code, or synonym.
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "query": "",
            "total_results": 0,
            "results": [],
            "message": "Please enter a search term or code."
        }

    results = knowledge_db.search_concepts(
        query=clean_query,
        medical_system=medical_system,
        concept_type=concept_type,
        limit=limit
    )

    for item in results:
        sys_key = (item.get("medical_system") or "").lower()
        c_term = item.get("term", "")
        meds = get_prescribed_medicines_for_term(c_term).get(sys_key, [])
        if not meds:
            meds = get_prescribed_medicines_for_term(clean_query).get(sys_key, [])
        item["prescribed_medicines"] = meds

    return {
        "query": clean_query,
        "filter_system": medical_system or "all",
        "filter_type": concept_type or "all",
        "total_results": len(results),
        "results": results,
        "disclaimer": (
            "Results are from official knowledge sources for educational purposes. "
            "Terminology mappings do not establish clinical equivalence."
        )
    }


def get_concept(concept_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves full details for a single concept by ID."""
    return knowledge_db.get_concept_details(concept_id)


import re
from typing import Dict, List, Any

PRESCRIBED_MEDICINES_DATA = [
    {
        "keywords": ["dengue", "dengue fever", "breakbone"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Paracetamol 650mg / Acetaminophen",
                    "action": "Antipyretic of Choice",
                    "details": "Strictly avoid Aspirin, Ibuprofen, and other NSAIDs due to severe bleeding & platelet dysfunction risks in dengue.",
                    "dosage": "650mg orally every 6 hours SOS after meals (Max 3-4g/day)"
                },
                {
                    "name": "Oral Rehydration Salts (ORS) & IV Fluid Resuscitation",
                    "action": "Electrolyte & Fluid Restoration",
                    "details": "Critical supportive therapy to compensate for capillary leakage and prevent dengue shock syndrome.",
                    "dosage": "Continuous oral/IV fluid intake titrated against urine output and hematocrit"
                },
                {
                    "name": "Complete Blood Count & Platelet Monitoring",
                    "action": "Clinical Vigilance",
                    "details": "Daily laboratory hematocrit and thrombocyte monitoring; platelet transfusion considered if severe bleeding or <20,000/mcL.",
                    "dosage": "CBC laboratory monitoring every 12-24 hours"
                }
            ],
            "ayurveda": [
                {
                    "name": "Carica Papaya Leaf Extract (पपीता स्वरस / Platmax / Caripill)",
                    "action": "Thrombocyte / Platelet Support",
                    "details": "Clinically proven to upregulate ALOX12 and PTAFR genes to boost blood platelet counts.",
                    "dosage": "1 tablet (1100mg extract) 3 times daily or 15-20ml fresh leaf juice"
                },
                {
                    "name": "Giloy Ghanvati (गिलोय घनवटी / Tinospora cordifolia)",
                    "action": "Rasayana & Immunomodulator",
                    "details": "Classical antipyretic herb that stabilizes vital capacity and purifies Pitta.",
                    "dosage": "1-2 tablets twice daily with lukewarm water"
                },
                {
                    "name": "Amritarishta (अमृतारिष्ट)",
                    "action": "Fermented Guduchi Tonic",
                    "details": "Liquid formulation to clear lingering viral toxins, restore appetite, and enhance immunity.",
                    "dosage": "15-20 ml twice daily with equal water after meals"
                },
                {
                    "name": "Sudarshan Vati (सुदर्शन वटी)",
                    "action": "Classical Antipyretic Vati",
                    "details": "Premier Ayurvedic bitter herbal formulation for acute, chronic, and viral fevers.",
                    "dosage": "1-2 tablets twice daily with warm water"
                }
            ],
            "homeopathy": [
                {
                    "name": "Eupatorium Perfoliatum 30C",
                    "action": "Prime Remedy for 'Bone-Break' Fever",
                    "details": "Specific for severe aching in bones and muscles as if broken, headache with pain in eyeballs, and bilious vomiting.",
                    "dosage": "4 pills every 2-3 hours during acute febrile stage"
                },
                {
                    "name": "Ipecacuanha 30C",
                    "action": "Gastric & Nausea Relief",
                    "details": "Indicated when persistent nausea, retching, and gastric discomfort accompany the viral fever.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Gelsemium Sempervirens 30C",
                    "action": "Dullness & Muscular Heaviness",
                    "details": "Marked prostration, heavy droopy eyelids, absence of thirst, and severe occipital headache.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Crotalus Horridus 30C",
                    "action": "Hemorrhagic Diathesis Protection",
                    "details": "Prescribed as a supportive homeopathic remedy when petechial spots or hemorrhagic signs occur.",
                    "dosage": "4 pills twice daily under qualified homeopathic care"
                }
            ]
        }
    },
    {
        "keywords": ["typhoid", "enteric fever", "salmonella", "sannipata jvara"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Azithromycin 500mg / Tab. Ciprofloxacin 500mg",
                    "action": "Bactericidal Antibiotic Therapy",
                    "details": "First-line oral antibiotic therapy targeted against Salmonella enterica serotype Typhi.",
                    "dosage": "500mg once daily for 7-10 days under medical prescription"
                },
                {
                    "name": "Inj. Ceftriaxone 1g-2g",
                    "action": "Third-Generation Cephalosporin",
                    "details": "Administered intravenously in complicated or multidrug-resistant enteric fever cases.",
                    "dosage": "1g IV twice daily for 7-14 days in hospital setting"
                },
                {
                    "name": "Tab. Paracetamol 650mg",
                    "action": "Antipyretic",
                    "details": "Oral antipyretic for step-ladder high fever control.",
                    "dosage": "650mg every 6 hours SOS"
                }
            ],
            "ayurveda": [
                {
                    "name": "Sanjivani Vati (सञ्जीवनी वटी)",
                    "action": "Digestive & Antitoxic Formulation",
                    "details": "Classical compound with Vidanga, Pippali, Haritaki, and Shuddha Bhallataka for intestinal Ama fevers.",
                    "dosage": "1 tablet twice daily with fresh ginger tea or warm water"
                },
                {
                    "name": "Sudarshan Vati (सुदर्शन वटी)",
                    "action": "Deepana & Jvaraghna",
                    "details": "Eliminates deep-seated systemic toxins in chronic enteric and prolonged fevers.",
                    "dosage": "2 tablets twice daily after meals"
                },
                {
                    "name": "Praval Pishti (प्रवाल पिष्टी)",
                    "action": "Natural Coral Calcium Antipyretic",
                    "details": "Cooling calx formulation that pacifies intense internal Pitta burning and thirst.",
                    "dosage": "125-250mg twice daily with honey or butter"
                }
            ],
            "homeopathy": [
                {
                    "name": "Baptisia Tinctoria 30C",
                    "action": "Septic & Typhoid Fever Sovereign Remedy",
                    "details": "Indicated for stupor, delirium, besotted dark-red face, offensive breath and sweat, and feeling 'broken in pieces'.",
                    "dosage": "4 pills every 2-3 hours in acute phase"
                },
                {
                    "name": "Arsenicum Album 30C",
                    "action": "Prostration & Burning Thirst",
                    "details": "Great restlessness, drinking small sips of water frequently, burning heat, and nocturnal anxiety.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Rhus Toxicodendron 30C",
                    "action": "Restlessness with Red Triangle Tongue",
                    "details": "Dry tongue with distinct red triangular tip; physical restlessness, worse lying still.",
                    "dosage": "4 pills 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["malaria", "marsh fever", "plasmodium", "vishama jvara", "vishama-jvara"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Artemether + Lumefantrine (Coartem)",
                    "action": "Artemisinin-Based Combination Therapy (ACT)",
                    "details": "WHO gold standard first-line oral antimalarial treatment for uncomplicated P. falciparum.",
                    "dosage": "4 tablets at 0h, 8h, 24h, 36h, 48h, and 60h with fatty meal"
                },
                {
                    "name": "Tab. Primaquine 15mg",
                    "action": "Radical Cure Hypnozoiticide",
                    "details": "Eradicates dormant liver hypnozoites in P. vivax to prevent relapses (Check G6PD first).",
                    "dosage": "15mg daily for 14 days after negative G6PD screening"
                },
                {
                    "name": "Tab. Paracetamol 650mg",
                    "action": "Antipyretic",
                    "details": "Temperature regulation during paroxysms.",
                    "dosage": "650mg orally every 6 hours SOS"
                }
            ],
            "ayurveda": [
                {
                    "name": "Ayush-64 (आयुष-६४)",
                    "action": "CCRAS Verified Anti-Malarial Formulation",
                    "details": "Composed of Saptaparna, Katuki, Chirayata, and Kuberaksha; proven clinical efficacy in malaria and viral fevers.",
                    "dosage": "2 tablets (500mg each) thrice daily with warm water for 5-7 days"
                },
                {
                    "name": "Mahasudarshan Churna (महासुदर्शन चूर्ण)",
                    "action": "Classical Bitter Antipyretic",
                    "details": "Relieves cyclical chill-fever-sweat paroxysms of Vishama Jvara.",
                    "dosage": "3 grams twice daily with warm water"
                },
                {
                    "name": "Kiratatikta / Chirayata (Swertia chirata)",
                    "action": "Bitter Liver Tonic & Febrifuge",
                    "details": "Purifies blood and clears malarial splenomegaly.",
                    "dosage": "Decoction (Kwath) 20-30ml twice daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Cinchona Officinalis (China) 30C",
                    "action": "Intermittent Paroxysmal Fever",
                    "details": "Historical source of quinine; indicated for periodic chills, debilitating night sweats, and sensitivity to cold air.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Natrum Muriaticum 30C",
                    "action": "Chill at 10-11 AM with Fever Blisters",
                    "details": "Malarial paroxysms with chill commencing between 10 AM and 11 AM, bursting frontal headache, and hydroa.",
                    "dosage": "4 pills twice daily"
                },
                {
                    "name": "Arsenicum Album 30C",
                    "action": "Periodic Chills & Prostration",
                    "details": "Irregular malarial paroxysms with profound exhaustion, burning sensation, and thirst.",
                    "dosage": "4 pills 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["fever", "pyrexia", "febrile", "temperature", "jvara", "jvarah", "shita jvara"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Paracetamol 650mg / Acetaminophen",
                    "action": "Antipyretic & Analgesic",
                    "details": "First-line oral medicine to reduce elevated body temperature and relieve generalized body aches.",
                    "dosage": "650mg orally every 4-6 hours SOS after meals (Max 4g/day)"
                },
                {
                    "name": "Tab. Ibuprofen 400mg",
                    "action": "NSAID Antipyretic",
                    "details": "Anti-inflammatory and temperature-reducing agent for fever accompanied by prominent inflammatory pain.",
                    "dosage": "1 tablet twice daily after meals SOS"
                },
                {
                    "name": "Tab. Mefenamic Acid 500mg (Meftal)",
                    "action": "Analgesic & Antipyretic",
                    "details": "Prescribed for resistant high-grade fevers when paracetamol alone is insufficient.",
                    "dosage": "1 tablet with food SOS"
                }
            ],
            "ayurveda": [
                {
                    "name": "Sudarshan Vati (सुदर्शन वटी)",
                    "action": "Classical Antipyretic Vati",
                    "details": "Premier Ayurvedic bitter herbal formulation for acute, chronic, and intermittent fevers.",
                    "dosage": "1-2 tablets twice daily with lukewarm water"
                },
                {
                    "name": "Mahasudarshan Churna (महासुदर्शन चूर्ण)",
                    "action": "Bitter Antipyretic Compound",
                    "details": "Traditional compound containing 53 herbs led by Kiratatikta; clears Ama and pacifies Pitta-Kapha.",
                    "dosage": "3-5 grams twice daily with warm water"
                },
                {
                    "name": "Amritarishta (अमृतारिष्ट)",
                    "action": "Fermented Guduchi Tonic",
                    "details": "Liquid formulation to clear lingering fever, restore appetite, and enhance immunity.",
                    "dosage": "15-20 ml twice daily with equal water after meals"
                },
                {
                    "name": "Giloy Ghanvati (गिलोय घनवटी / Tinospora cordifolia)",
                    "action": "Rasayana & Immunomodulator",
                    "details": "Antipyretic botanical extract that stabilizes platelet counts and neutralizes internal toxins.",
                    "dosage": "1-2 tablets twice daily with water"
                },
                {
                    "name": "Tribhuvan Kirti Ras (त्रिभुवनकीर्ति रस)",
                    "action": "Herbo-Mineral Antipyretic",
                    "details": "Fast-acting classical formulation indicated for fevers accompanied by cold and cough.",
                    "dosage": "1 tablet twice daily with honey or ginger juice"
                }
            ],
            "homeopathy": [
                {
                    "name": "Aconitum Napellus 30C",
                    "action": "Acute Febrile Onset",
                    "details": "Key remedy for sudden high fever following cold dry wind exposure, with restlessness and anxiety.",
                    "dosage": "4 pills 3-4 times daily or every 2 hours in acute phase"
                },
                {
                    "name": "Belladonna 30C",
                    "action": "Congestive & Throbbing Fever",
                    "details": "High fever with intensely red flushed face, throbbing headache, and burning skin.",
                    "dosage": "4 pills 3 times daily dissolved on tongue"
                },
                {
                    "name": "Bryonia Alba 30C",
                    "action": "Fever with Intense Thirst",
                    "details": "Dry cracked lips, great thirst for cold water; bodily pains aggravated by slightest movement.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Ferrum Phosphoricum 6X / 30C",
                    "action": "First Stage Inflammatory Fever",
                    "details": "Biochemic tissue remedy for onset of febrile state with flushed cheeks and soft pulse.",
                    "dosage": "4 tablets 3 times daily dissolved in warm water"
                },
                {
                    "name": "Gelsemium Sempervirens 30C",
                    "action": "Dull Febrile Prostration",
                    "details": "Marked weakness, drowsiness, heavy droopy eyelids, muscular aching, and absence of thirst.",
                    "dosage": "4 pills 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["diabetes", "sugar", "madhumeha", "prameha", "hyperglycemia", "glucose", "diabetic"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Metformin 500mg / 1000mg",
                    "action": "Biguanide Insulin Sensitizer",
                    "details": "First-line oral antidiabetic reducing hepatic gluconeogenesis and improving peripheral insulin uptake.",
                    "dosage": "500mg-1000mg twice daily with or after meals"
                },
                {
                    "name": "Tab. Glimepiride 1mg / 2mg",
                    "action": "Second-Generation Sulfonylurea",
                    "details": "Stimulates pancreatic beta-cells to secrete insulin in response to elevated blood glucose.",
                    "dosage": "1mg-2mg once daily before breakfast"
                },
                {
                    "name": "Tab. Sitagliptin 100mg / Vildagliptin 50mg",
                    "action": "DPP-4 Inhibitor (Gliptin)",
                    "details": "Prolongs active incretin hormones (GLP-1), enhancing meal-dependent insulin release.",
                    "dosage": "100mg once daily orally"
                },
                {
                    "name": "Tab. Empagliflozin 10mg / Dapagliflozin 10mg",
                    "action": "SGLT2 Inhibitor",
                    "details": "Increases urinary glucose excretion while providing proven renal and cardiovascular benefits.",
                    "dosage": "10mg once daily in the morning"
                }
            ],
            "ayurveda": [
                {
                    "name": "Chandraprabha Vati (चन्द्रप्रभावटी)",
                    "action": "Classical Prameha Rasayana",
                    "details": "Clears microvascular urinary tract congestion, regulates glucose excretion, and combats fatigue.",
                    "dosage": "1-2 tablets twice daily with warm water or milk"
                },
                {
                    "name": "Vasant Kusumakar Ras (वसंत कुसुमाकर रस)",
                    "action": "Premium Herbo-Mineral Gold Rejuvenator",
                    "details": "Formulated with Swarna, Rajata, and Praval Bhasma for long-standing diabetic debility and neuropathy.",
                    "dosage": "1 tablet (125mg) daily with honey or milk"
                },
                {
                    "name": "Nishamalaki Churna (निशामलकी)",
                    "action": "Haridra + Amalaki Compound",
                    "details": "Classic combination of turmeric and Indian gooseberry that protects beta-cell microcirculation.",
                    "dosage": "3 grams twice daily with warm water before meals"
                },
                {
                    "name": "Shuddha Shilajit (शुद्ध शिलाजीत)",
                    "action": "Bio-Mineral Fulvic Rasayana",
                    "details": "Improves cellular insulin sensitivity and relieves chronic diabetic lethargy.",
                    "dosage": "250-500mg twice daily with warm milk"
                },
                {
                    "name": "Jamun (Syzygium cumini) & Karela Seed Churna",
                    "action": "Botanical Hypoglycemic",
                    "details": "Contains jamboline and charantin to curb postprandial glucose surges.",
                    "dosage": "3-5 grams twice daily before food"
                }
            ],
            "homeopathy": [
                {
                    "name": "Syzygium Jambolanum Q (Mother Tincture)",
                    "action": "Glycosuria & Blood Sugar Regulator",
                    "details": "Premier homeopathic mother tincture from black plum; reduces specific gravity of urine and thirst.",
                    "dosage": "10-15 drops in half a cup of water thrice daily before meals"
                },
                {
                    "name": "Uranium Nitricum 3X",
                    "action": "Diabetic Metabolic Restorative",
                    "details": "Indicated in diabetes mellitus with profound emaciation, voracious appetite, polyuria, and fatigue.",
                    "dosage": "2 tablets twice daily"
                },
                {
                    "name": "Phosphoricum Acidum 30C",
                    "action": "Mental & Physical Prostration",
                    "details": "Diabetes of nervous origin or following emotional grief; profuse clear watery urination.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Gymnema Sylvestre Q (Mother Tincture)",
                    "action": "Sugar-Destroying Herb (Gurmar)",
                    "details": "Suppresses craving for sugary foods and supports pancreatic endocrine tone.",
                    "dosage": "10 drops in water twice daily"
                }
            ]
        }
    },
    {
        "keywords": ["hypertension", "blood pressure", "high bp", "raktagata vata", "raktachapa"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Amlodipine 5mg",
                    "action": "Dihydropyridine Calcium Channel Blocker",
                    "details": "Inhibits calcium influx into arterial smooth muscle, causing peripheral vasodilation.",
                    "dosage": "5mg orally once daily in the morning"
                },
                {
                    "name": "Tab. Telmisartan 40mg / Tab. Losartan 50mg",
                    "action": "Angiotensin II Receptor Blocker (ARB)",
                    "details": "Blocks AT1 receptors, lowering systemic vascular resistance and providing kidney protection.",
                    "dosage": "40mg-80mg once daily orally"
                },
                {
                    "name": "Tab. Atenolol 50mg / Tab. Metoprolol 25mg",
                    "action": "Cardioselective Beta-1 Blocker",
                    "details": "Decreases heart rate, myocardial contractility, and cardiac output in stress-induced hypertension.",
                    "dosage": "25mg-50mg once daily"
                },
                {
                    "name": "Tab. Ramipril 2.5mg / Enalapril 5mg",
                    "action": "ACE Inhibitor",
                    "details": "Suppresses conversion of angiotensin I to II, decreasing afterload and vascular remodeling.",
                    "dosage": "2.5mg-5mg once daily"
                }
            ],
            "ayurveda": [
                {
                    "name": "Sarpagandha Ghanvati (सर्पगंधा घनवटी)",
                    "action": "Classical Rauwolfia Serpentina Extract",
                    "details": "Natural reserpine alkaloid formulation that calms hyperactive sympathetic nervous tone.",
                    "dosage": "1 tablet at bedtime with warm water"
                },
                {
                    "name": "Mukta Vati (मुक्ता वटी)",
                    "action": "Pearl & Calming Herbal Compound",
                    "details": "Formulated with Mukta Pishti, Shankhpushpi, and Jatamansi for arterial hypertension with anxiety.",
                    "dosage": "1-2 tablets twice daily with water"
                },
                {
                    "name": "Brahmi Vati (ब्राह्मी वटी)",
                    "action": "Neuro-Cardiovascular Calmative",
                    "details": "Regulates autonomic emotional reactivity and decreases pressure spikes due to stress.",
                    "dosage": "1 tablet twice daily after food"
                },
                {
                    "name": "Arjuna Churna / Ksheerapaka (अर्जुन छाल)",
                    "action": "Premier Cardiotonic Bark",
                    "details": "Co-Q10 rich tree bark that tones the heart muscle and maintains arterial lumen elasticity.",
                    "dosage": "3-5 grams boiled in milk (Ksheerapaka) once daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Rauwolfia Serpentina Q (Mother Tincture)",
                    "action": "Natural Hypotensive Tincture",
                    "details": "Lowers systolic and diastolic blood pressure without depressing myocardial contractility.",
                    "dosage": "10-15 drops in water twice daily after meals"
                },
                {
                    "name": "Glonoine 30C",
                    "action": "Congestive Arterial Pulsation",
                    "details": "Hypertension with surging headache, throbbing temporal vessels, sensation that head will burst.",
                    "dosage": "4 pills dissolved on tongue SOS"
                },
                {
                    "name": "Crataegus Oxyacantha Q (Hawthorn Tincture)",
                    "action": "Cardiotonic Botanical",
                    "details": "Dissolves arterial crusts, relieves high arterial tension, and tones weak cardiac musculature.",
                    "dosage": "10 drops in water twice daily"
                },
                {
                    "name": "Baryta Carbonica 30C",
                    "action": "Arteriosclerotic Hypertension in Elderly",
                    "details": "Indicated in elderly individuals with hardened arteries, loss of memory, and elevated systolic BP.",
                    "dosage": "4 pills twice weekly"
                }
            ]
        }
    },
    {
        "keywords": ["cough", "cold", "bronchitis", "pharyngitis", "sore throat", "kasa", "pratishyaya", "rhinitis"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Syrup Dextromethorphan + Chlorpheniramine",
                    "action": "Antitussive & Antihistamine",
                    "details": "Centrally acting NMDA receptor blocker that quiets irritating, non-productive dry cough.",
                    "dosage": "10ml orally three times daily as needed"
                },
                {
                    "name": "Syrup Ambroxol + Guaiphenesin + Terbutaline",
                    "action": "Mucolytic Bronchodilator Expectorant",
                    "details": "Cleaves mucopolysaccharide fibers in sticky phlegm and dilates airways for productive chest cough.",
                    "dosage": "10ml orally thrice daily after meals"
                },
                {
                    "name": "Tab. Levocetirizine 5mg + Montelukast 10mg",
                    "action": "Antiallergic & Leukotriene Blocker",
                    "details": "Controls nocturnal cough spasms, allergic rhinitis, and post-nasal drip.",
                    "dosage": "1 tablet at bedtime"
                },
                {
                    "name": "Tab. Azithromycin 500mg",
                    "action": "Macrolide Antibiotic",
                    "details": "Indicated when secondary purulent bacterial infection or acute bronchitis is confirmed.",
                    "dosage": "500mg once daily for 3-5 days"
                }
            ],
            "ayurveda": [
                {
                    "name": "Sitopaladi Churna (सितोपलादि चूर्ण)",
                    "action": "Classical Respiratory Demulcent",
                    "details": "Bambusa (Vanshlochan), Pippali, Ela, and Cinnamon; soothes inflamed throat and chest.",
                    "dosage": "3 grams mixed with 1 teaspoon pure honey 3 times daily"
                },
                {
                    "name": "Talisadi Churna (तालीसादि चूर्ण)",
                    "action": "Warming Bronchial Expectorant",
                    "details": "Talisapatra compound that clears heavy Kapha phlegm and restores digestive agni.",
                    "dosage": "3 grams with warm water or honey twice daily"
                },
                {
                    "name": "Vasavaleha (वासावलेह)",
                    "action": "Adhatoda Vasica Herbal Jam",
                    "details": "Potent natural bronchodilator and mucolytic paste for stubborn wheezing and chronic cough.",
                    "dosage": "1 teaspoon (5-10g) twice daily after meals"
                },
                {
                    "name": "Lavangadi Vati (लवङ्गादि वटी)",
                    "action": "Clove & Licorice Throat Chewable",
                    "details": "Chewed slowly in mouth to instantly suppress tickling throat cough and laryngitis.",
                    "dosage": "1 tablet sucked slowly 3-4 times daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Drosera Rotundifolia 30C",
                    "action": "Spasmodic Paroxysmal Cough",
                    "details": "Dry barking cough coming in rapid fits, worse as soon as head touches pillow at night.",
                    "dosage": "4 pills 3-4 times daily"
                },
                {
                    "name": "Bryonia Alba 30C",
                    "action": "Painful Dry Cough",
                    "details": "Must hold chest with hands when coughing; cough hurts head and chest, worsened by movement.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Hepar Sulphur 30C",
                    "action": "Cold Air Sensitivity",
                    "details": "Loose rattling cough triggered by the slightest draft of cold air or uncovering.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Antimonium Tartaricum 30C",
                    "action": "Rattling Chest Mucus with Weakness",
                    "details": "Lungs feel loaded with mucus that rattles on respiration, but patient is too weak to expectorate.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Justicia Adhatoda Q (Mother Tincture)",
                    "action": "Botanical Cough Expectorant",
                    "details": "Acute catarrhal cough with suffocative constriction in windpipe.",
                    "dosage": "10 drops in warm water thrice daily"
                }
            ]
        }
    },
    {
        "keywords": ["headache", "migraine", "cephalalgia", "shirashula", "shiroshula", "head ache"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Paracetamol 650mg / Tab. Ibuprofen 400mg",
                    "action": "Analgesic & NSAID",
                    "details": "First-line oral medications for tension headaches and mild-to-moderate vascular headaches.",
                    "dosage": "1 tablet after meals SOS (Max 3 doses/day)"
                },
                {
                    "name": "Tab. Naproxen 500mg",
                    "action": "Long-Acting NSAID",
                    "details": "Sustained analgesic relief for prolonged throbbing hemicrania.",
                    "dosage": "500mg initially, then 250mg every 8 hours SOS"
                },
                {
                    "name": "Tab. Sumatriptan 50mg / Rizatriptan 10mg",
                    "action": "5-HT1B/1D Receptor Agonist",
                    "details": "Specific abortive therapy for acute severe migraine attacks; causes cranial vasoconstriction.",
                    "dosage": "50mg at onset of migraine; may repeat once after 2 hours if needed"
                },
                {
                    "name": "Tab. Flunarizine 10mg",
                    "action": "Calcium Channel Prophylaxis",
                    "details": "Daily preventive medication for recurrent migraine sufferers to decrease attack frequency.",
                    "dosage": "10mg once daily at bedtime"
                }
            ],
            "ayurveda": [
                {
                    "name": "Shirashooladi Vajra Ras (शिरःशूलादि वज्र रस)",
                    "action": "Premier Classical Cephalalgia Formulation",
                    "details": "Contains Guggulu, Triphala, and mineral calces; treats unilateral Suryavarta and Ardhavabhedaka (migraine).",
                    "dosage": "1-2 tablets twice daily with goat's milk or warm water"
                },
                {
                    "name": "Pathyadi Kadha (पथ्यादि क्वाथ)",
                    "action": "Triphala Decoction for Migraines",
                    "details": "Clears ocular pressure and Pitta-Vata vitiation that triggers temporal vascular throbbing.",
                    "dosage": "15-20ml mixed with equal water twice daily before meals"
                },
                {
                    "name": "Godanti Bhasma (गोदन्ती भस्म)",
                    "action": "Natural Gypsum Calx Analgesic",
                    "details": "Fast-acting cooling calx that relieves burning temple pain and fever-induced headaches.",
                    "dosage": "250-500mg with honey or ghee twice daily"
                },
                {
                    "name": "Anu Taila (अणु तैल - Nasya Oil)",
                    "action": "Nasal Medication (Shirovirechana)",
                    "details": "2 drops instilled in each nostril in morning to clear sinuses and open cranial micro-channels.",
                    "dosage": "2 drops per nostril daily in morning on empty stomach"
                }
            ],
            "homeopathy": [
                {
                    "name": "Belladonna 30C",
                    "action": "Throbbing Congestive Headache",
                    "details": "Violent throbbing in temples, flushed face, headache worse by light, noise, motion, or lying flat.",
                    "dosage": "4 pills every hour during acute headache, then 3 times daily"
                },
                {
                    "name": "Spigelia Anthelmia 30C",
                    "action": "Left-Sided Neuralgic Migraine",
                    "details": "Pain begins in morning at occiput, travels forward and settles fiercely over left eye.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Glonoine 30C",
                    "action": "Pulsating Sun & Heat Headache",
                    "details": "Sensation that head will explode with each heartbeat; worse from sun exposure or warmth.",
                    "dosage": "4 pills dissolved on tongue SOS"
                },
                {
                    "name": "Natrum Muriaticum 30C",
                    "action": "Hammering Anemic Migraine",
                    "details": "Pain like thousand little hammers beating inside skull, triggered by eye strain or emotional stress.",
                    "dosage": "4 pills twice daily"
                }
            ]
        }
    },
    {
        "keywords": ["asthma", "wheezing", "breathless", "dyspnea", "shwasa", "tamaka shwasa", "copd"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Salbutamol (Albuterol) Inhaler 100mcg",
                    "action": "Short-Acting Beta-2 Agonist (SABA)",
                    "details": "Immediate rescue bronchodilator for rapid relief of acute wheezing and chest tightness.",
                    "dosage": "1-2 puffs via spacer during acute bronchospasm SOS"
                },
                {
                    "name": "Budesonide + Formoterol Inhaler (Symbicort / Foracort 200)",
                    "action": "Inhaled Corticosteroid (ICS) + LABA",
                    "details": "Maintenance controller therapy reducing airway mucosal inflammation and preventing attacks.",
                    "dosage": "1-2 puffs twice daily; rinse mouth with water after inhalation"
                },
                {
                    "name": "Tab. Montelukast 10mg",
                    "action": "Leukotriene Receptor Antagonist",
                    "details": "Suppresses inflammatory leukotrienes to decrease exercise-induced and nocturnal asthma flares.",
                    "dosage": "10mg once daily at bedtime"
                },
                {
                    "name": "Tab. Doxofylline 400mg",
                    "action": "Xanthine Bronchodilator",
                    "details": "Relaxes smooth muscle fibers around bronchial tree with minimal cardiac stimulation.",
                    "dosage": "400mg once or twice daily after food"
                }
            ],
            "ayurveda": [
                {
                    "name": "Shwas Kuthar Ras (श्वासकुठार रस)",
                    "action": "Emergency Bronchodilator Tablet",
                    "details": "Classical herbo-mineral compound containing Shuddha Parada, Gandhak, and Trikatu for airway spasm.",
                    "dosage": "1 tablet twice daily with betel leaf juice or warm water"
                },
                {
                    "name": "Kanakasava (कनकासव)",
                    "action": "Datura & Licorice Bronchial Tonic",
                    "details": "Natural anticholinergic liquid formulation that dilates constricted bronchioles and liquefies phlegm.",
                    "dosage": "15-20ml mixed with equal water twice daily after meals"
                },
                {
                    "name": "Shwasakasa Chintamani Ras",
                    "action": "Swarna & Pearl Respiratory Rasayana",
                    "details": "Premium rejuvenating formulation for chronic asthmatic emphysema and weak lung vital capacity.",
                    "dosage": "1 tablet (125mg) twice daily with honey"
                },
                {
                    "name": "Somlata & Bharangi Churna",
                    "action": "Natural Anti-Allergic Bronchodilator",
                    "details": "Inhibits histamine release and relaxes spasmodic tracheobronchial musculature.",
                    "dosage": "3 grams twice daily with lukewarm water"
                }
            ],
            "homeopathy": [
                {
                    "name": "Arsenicum Album 30C",
                    "action": "Nocturnal Suffocative Asthma",
                    "details": "Attacks worst between midnight and 2 AM; patient cannot lie down, must sit bent forward with anxiety.",
                    "dosage": "4 pills 3 times daily or during attack"
                },
                {
                    "name": "Blatta Orientalis Q / 3X",
                    "action": "Specific for Asthmatic Bronchitis",
                    "details": "Prepared from cockroach; proven clinical efficacy in acute asthma with abundant yellow phlegm.",
                    "dosage": "10 drops in warm water thrice daily"
                },
                {
                    "name": "Aspidosperma Q (Mother Tincture)",
                    "action": "'Digitalis of the Lungs' Oxygenator",
                    "details": "Stimulates respiratory centers, increasing blood oxygenation during severe asthma attacks.",
                    "dosage": "10-15 drops in water thrice daily"
                },
                {
                    "name": "Ipecacuanha 30C",
                    "action": "Incessant Coughing with Retching",
                    "details": "Spasmodic chest constriction with incessant dry cough, gagging, vomiting, and loose rattling mucus.",
                    "dosage": "4 pills 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["acidity", "acid reflux", "gerd", "gastritis", "heartburn", "amlapitta", "ajirna", "indigestion", "dyspepsia"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Pantoprazole 40mg / Omeprazole 20mg / Rabeprazole 20mg",
                    "action": "Proton Pump Inhibitor (PPI)",
                    "details": "Irreversibly inhibits H+/K+ ATPase enzyme in gastric parietal cells, shutting down acid production.",
                    "dosage": "40mg orally once daily in morning 30 minutes before breakfast"
                },
                {
                    "name": "Antacid Suspension (Magaldrate + Simethicone Gel)",
                    "action": "Chemical Neutralizer & Demulcent",
                    "details": "Rapid chemical neutralization of gastric acid with simethicone to coalesce gas bubbles.",
                    "dosage": "10-15ml orally 1 hour after meals and at bedtime"
                },
                {
                    "name": "Tab. Domperidone 10mg / Levosulpiride 25mg",
                    "action": "Prokinetic Agent",
                    "details": "Promotes gastric emptying and increases lower esophageal sphincter tone to curb reflux.",
                    "dosage": "1 tablet before meals"
                }
            ],
            "ayurveda": [
                {
                    "name": "Avipattikar Churna (अविपत्तिकर चूर्ण)",
                    "action": "Premier Classical Antacid Compound",
                    "details": "Formulation with 14 herbs including Amla, Nishoth, and Cardamom; neutralizes sour Pitta and gently purges heat.",
                    "dosage": "3-5 grams twice daily with cold water or milk before meals"
                },
                {
                    "name": "Kamdudha Ras (कामदुधा रस - Moti Yukta)",
                    "action": "Calcium & Pearl Pitta Pacifier",
                    "details": "Alkaline calces (Mukta, Praval, Shukti, Shankha) that heal eroded gastric mucosal lining.",
                    "dosage": "250-500mg twice daily with honey or butter"
                },
                {
                    "name": "Shankh Bhasma (शंख भस्म)",
                    "action": "Purified Conch Shell Alkaline Calx",
                    "details": "Rapidly relieves sour burps, burning epigastric pain, and chronic gas distention.",
                    "dosage": "250mg twice daily with warm water"
                },
                {
                    "name": "Sutshekhar Ras (सूतशेखर रस)",
                    "action": "Gastric Harmonizer",
                    "details": "Relieves burning in chest, bilious vomiting, and severe dyspepsia.",
                    "dosage": "1 tablet twice daily before food"
                }
            ],
            "homeopathy": [
                {
                    "name": "Nux Vomica 30C",
                    "action": "Digestive Irritation & Reflux",
                    "details": "Specific for heartburn after spicy food, alcohol, tobacco, or late hours; weight in stomach after eating.",
                    "dosage": "4 pills at bedtime or 3 times daily"
                },
                {
                    "name": "Robinia Pseudacacia 30C",
                    "action": "Intensely Sour Eructations",
                    "details": "Excessive hyperchlorhydria; eructations and vomit so intensely acidic they set teeth on edge.",
                    "dosage": "4 pills after meals"
                },
                {
                    "name": "Carbo Vegetabilis 30C",
                    "action": "Upper Abdominal Flatulence & Bloating",
                    "details": "Heavy upper abdomen distention, fullness immediately after small meals; belching gives relief.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Natrum Phosphoricum 6X",
                    "action": "Biochemic Acid Neutralizer",
                    "details": "Biochemic tissue remedy for sour risings, heartburn, and creamy golden-yellow coating on back of tongue.",
                    "dosage": "4 tablets dissolved on tongue 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["arthritis", "joint pain", "gout", "rheumatism", "osteoarthritis", "sandhivata", "amavata", "rheumatoid"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Aceclofenac 100mg + Paracetamol 325mg",
                    "action": "NSAID & Analgesic Combination",
                    "details": "Inhibits COX-2 prostaglandin synthesis to relieve joint swelling, tenderness, and morning stiffness.",
                    "dosage": "1 tablet twice daily after meals"
                },
                {
                    "name": "Topical Diclofenac Gel 1% / 2%",
                    "action": "Direct Topical Anti-Inflammatory",
                    "details": "High localized synovial tissue penetration with minimal systemic GI exposure.",
                    "dosage": "Apply gently over affected joints 3-4 times daily"
                },
                {
                    "name": "Tab. Etoricoxib 90mg",
                    "action": "Selective COX-2 Inhibitor",
                    "details": "Rapid, once-daily relief for acute inflammatory flare-ups in gouty or osteoarthritic joints.",
                    "dosage": "90mg once daily after meals for 5-7 days"
                },
                {
                    "name": "Glucosamine Sulfate 1500mg + Chondroitin 1200mg",
                    "action": "Chondroprotective Cartilage Support",
                    "details": "Nutraceutical building blocks to maintain articular cartilage volume in chronic osteoarthritis.",
                    "dosage": "Once daily with food for at least 3 months"
                }
            ],
            "ayurveda": [
                {
                    "name": "Yograj Guggulu (योगराज गुग्गुलु)",
                    "action": "Purified Commiphora Mukul Resin Compound",
                    "details": "Classic anti-inflammatory that flushes deep Vata and Ama out of skeletal joints.",
                    "dosage": "2 tablets twice daily with warm water or Maharasnadi Kwath"
                },
                {
                    "name": "Maharasnadi Kwath (महारास्नादि क्वाथ)",
                    "action": "Decoction of 26 Anti-Vata Herbs",
                    "details": "Re-lubricates stiff joints, eases sciatica, and relieves generalized musculoskeletal stiffness.",
                    "dosage": "20ml with equal water twice daily after meals"
                },
                {
                    "name": "Shallaki (Boswellia serrata) Capsules 500mg",
                    "action": "Natural 5-LOX Inhibitor",
                    "details": "Boswellic acids decrease glycosaminoglycan degradation in knee and hip cartilage.",
                    "dosage": "1 capsule twice daily with meals"
                },
                {
                    "name": "Mahanarayan Taila (महानारायण तैल)",
                    "action": "Medicated Warm Sesame Massage Oil",
                    "details": "Formulated with 50+ herbs; massaged gently over joints followed by hot water fomentation.",
                    "dosage": "Apply warm oil over joints once or twice daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Rhus Toxicodendron 30C",
                    "action": "First Motion Aggravation, Relief on Continued Motion",
                    "details": "Joints stiff and aching upon beginning to move, but pain dramatically eases after moving about.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Bryonia Alba 30C",
                    "action": "Rest Relief, Aggravated by Motion",
                    "details": "Joints red, hot, swollen; sharp stitching pain on the slightest motion, relieved by firm pressure and resting.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Ledum Palustre 30C",
                    "action": "Ascending Joint Pain Relieved by Ice Cold",
                    "details": "Gouty pain in toes and ankles traveling upwards; joints paradoxically feel better with cold wet compresses.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Arnica Montana 30C",
                    "action": "Bruised Joint & Muscle Soreness",
                    "details": "Painful bruised soreness in joints as if beaten; fear of being touched or approached.",
                    "dosage": "4 pills twice daily"
                }
            ]
        }
    },
    {
        "keywords": ["allergy", "skin allergy", "urticaria", "rash", "itching", "eczema", "dermatitis", "hives", "sheetapitta", "kushta"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Levocetirizine 5mg / Cetirizine 10mg",
                    "action": "Second-Generation H1 Antihistamine",
                    "details": "Blocks peripheral histamine H1 receptors to rapidly resolve hives, skin wheals, and pruritus.",
                    "dosage": "1 tablet once daily at bedtime"
                },
                {
                    "name": "Tab. Hydroxyzine 25mg (Atarax)",
                    "action": "Sedative Antihistamine",
                    "details": "Controls intense nighttime cutaneous itching and breaks itch-scratch cycle.",
                    "dosage": "25mg once at bedtime as needed"
                },
                {
                    "name": "Topical Hydrocortisone 1% / Clobetasol 0.05% Cream",
                    "action": "Topical Corticosteroid",
                    "details": "Anti-inflammatory ointment applied thinly over localized eczematous patches.",
                    "dosage": "Apply thin layer twice daily for 5-7 days"
                },
                {
                    "name": "Calamine Lotion with Liquid Paraffin",
                    "action": "Cooling Demulcent Protectant",
                    "details": "Soothes irritated cutaneous nerve endings and cools inflamed skin surface.",
                    "dosage": "Apply liberally over itchy areas 3-4 times daily"
                }
            ],
            "ayurveda": [
                {
                    "name": "Haridra Khanda (हरिद्रा खण्ड)",
                    "action": "Classical Anti-Allergic Granules",
                    "details": "Turmeric, triphala, and warming spices cooked in cow's ghee; balances immune response against allergens.",
                    "dosage": "1 teaspoon (5g) twice daily with warm milk"
                },
                {
                    "name": "Khadirarishta (खदिरारिष्ट)",
                    "action": "Premier Blood Purifying Ferment",
                    "details": "Classical Acacia catechu tonic that eliminates deep Rakta and Twak metabolic impurities.",
                    "dosage": "15-20ml mixed with equal water twice daily after meals"
                },
                {
                    "name": "Kaishore Guggulu (कैशोर गुग्गुलु)",
                    "action": "Detoxifying Anti-Inflammatory Vati",
                    "details": "Guduchi and Triphala compound that clears aggravated Pitta causing burning rashes.",
                    "dosage": "2 tablets twice daily with water"
                },
                {
                    "name": "Gandhak Rasayan (गन्धक रसायन)",
                    "action": "Purified Sulfur Cellular Rasayana",
                    "details": "Natural antibacterial and anti-pruritic rejuvenator for chronic eczema and hives.",
                    "dosage": "1-2 tablets twice daily with milk"
                }
            ],
            "homeopathy": [
                {
                    "name": "Apis Mellifica 30C",
                    "action": "Stinging Hives with Rosy Swelling",
                    "details": "Allergic urticaria with sudden puffiness, stinging biting pains; relieved by cold water bathing.",
                    "dosage": "4 pills every 2-3 hours in acute phase"
                },
                {
                    "name": "Urtica Urens Q / 30C",
                    "action": "Nettle Rash Sovereign Remedy",
                    "details": "Intense burning, tingling hives with raised red welts, worse after warmth or exertion.",
                    "dosage": "10 drops in water or 4 pills 3 times daily"
                },
                {
                    "name": "Sulphur 30C",
                    "action": "Violent Itching Worse by Warmth",
                    "details": "Dry scaly eczema, intense itching that burns after scratching; worse from warm bath or heat of bed.",
                    "dosage": "4 pills once weekly"
                },
                {
                    "name": "Graphites 30C",
                    "action": "Sticky Honey-Like Exudate",
                    "details": "Eczema in skin folds (behind ears, groin, knees) exuding thick, glutinous, honey-like fluid.",
                    "dosage": "4 pills twice daily"
                }
            ]
        }
    },
    {
        "keywords": ["diarrhea", "diarrhoea", "loose motion", "loose stools", "gastroenteritis", "dysentery", "atisara", "pravahika"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Oral Rehydration Salts (ORS) + Zinc Gluconate 20mg",
                    "action": "WHO Essential Therapy",
                    "details": "Replenishes water, sodium, potassium, and bicarbonate to prevent dehydration; zinc accelerates gut mucosal healing.",
                    "dosage": "1 sachet in 1 liter clean water consumed after each loose stool; Zinc 20mg daily x 14 days"
                },
                {
                    "name": "Tab. Loperamide 2mg",
                    "action": "Peripheral Opioid Mu-Receptor Agonist",
                    "details": "Slows intestinal peristalsis in non-invasive watery diarrhea (Avoid in bloody dysentery or high fever).",
                    "dosage": "4mg initially, then 2mg after each loose stool (Max 16mg/day)"
                },
                {
                    "name": "Tab. Ofloxacin 200mg + Ornidazole 500mg",
                    "action": "Fluoroquinolone & Nitroimidazole",
                    "details": "Prescribed for acute bacterial enteritis, shigellosis, or amoebic dysentery with cramps.",
                    "dosage": "1 tablet twice daily after meals for 3-5 days"
                },
                {
                    "name": "Probiotic Capsules (Bacillus clausii / Saccharomyces boulardii)",
                    "action": "Microbiome Reconstitution",
                    "details": "Restores beneficial commensal flora and inhibits colonization by enteropathogens.",
                    "dosage": "1 capsule/vial twice daily for 5 days"
                }
            ],
            "ayurveda": [
                {
                    "name": "Kutajghan Vati (कुटजघन वटी)",
                    "action": "Premier Classical Botanical Astringent",
                    "details": "Holarrhena antidysenterica bark extract that consolidates intestinal motility and terminates bacterial diarrhea.",
                    "dosage": "2 tablets twice daily with warm water or buttermilk"
                },
                {
                    "name": "Bilvadi Churna (बिल्वादि चूर्ण)",
                    "action": "Unripe Bael Fruit & Spices Binder",
                    "details": "Astringent digestive formula that absorbs excess fluid and soothes intestinal inflammation.",
                    "dosage": "3 grams twice daily with buttermilk (Takra)"
                },
                {
                    "name": "Gangadhar Churna (गङ्गाधर चूर्ण)",
                    "action": "Classical Sangrahi Compound",
                    "details": "Contains Musta, Bilva, and Lodhra; halts persistent watery evacuations.",
                    "dosage": "3 grams twice daily with honey or rice water"
                },
                {
                    "name": "Mustakarishta (मुस्तारिष्ट)",
                    "action": "Digestive Fire (Agni) Rebuilder",
                    "details": "Cyperus rotundus ferment that corrects intestinal dysbiosis and cures dysentery.",
                    "dosage": "15ml with equal water twice daily after meals"
                }
            ],
            "homeopathy": [
                {
                    "name": "Podophyllum Peltatum 30C",
                    "action": "Painless Gushing Morning Stool",
                    "details": "Profuse, watery, gushing, fetid stool that empties the entire rectum, followed by extreme exhaustion.",
                    "dosage": "4 pills after each bowel movement"
                },
                {
                    "name": "Arsenicum Album 30C",
                    "action": "Food Poisoning & Traveler's Diarrhea",
                    "details": "Diarrhea after spoiled meat, contaminated water, or cold melons with burning abdominal cramps and prostration.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Aloe Socotrina 30C",
                    "action": "Sphincter Weakness & Urgency",
                    "details": "Sudden violent urge for stool immediately after eating or drinking; uncertain whether gas or stool will pass.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Mercurius Corrosivus 30C",
                    "action": "Severe Tenesmus & Bloody Dysentery",
                    "details": "Agonizing straining before, during, and after stool; stool contains shreds of mucus and blood.",
                    "dosage": "4 pills 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["constipation", "sluggish bowel", "hard stool", "vibandha", "anaha"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Syrup Lactulose 10g/15ml",
                    "action": "Synthetic Disaccharide Osmotic Laxative",
                    "details": "Fermented by colonic bacteria into lactic acid, drawing water into bowel lumen to soften hard stools.",
                    "dosage": "15-30ml orally at bedtime with plenty of water"
                },
                {
                    "name": "Ispaghula (Psyllium) Husk 5-10g",
                    "action": "Bulk-Forming Soluble Mucilage",
                    "details": "Absorbs water in intestines to form soft, bulky stool that stimulates natural peristalsis.",
                    "dosage": "1-2 tablespoons stirred in glass of water immediately before bedtime"
                },
                {
                    "name": "Tab. Bisacodyl 5mg / 10mg",
                    "action": "Diphenylmethane Stimulant Laxative",
                    "details": "Directly excites sensory nerve endings in colonic wall for predictable morning evacuation.",
                    "dosage": "5-10mg orally at bedtime as needed SOS"
                },
                {
                    "name": "Polyethylene Glycol (PEG) 3350 Powder",
                    "action": "Iso-Osmotic Stool Softener",
                    "details": "Non-absorbable polymer that retains water in stool without systemic electrolyte disturbance.",
                    "dosage": "17g dissolved in 200ml water once daily"
                }
            ],
            "ayurveda": [
                {
                    "name": "Triphala Churna (त्रिफला चूर्ण)",
                    "action": "Three-Fruits Rejuvenator",
                    "details": "Haritaki, Bibhitaki, and Amalaki; tones colon muscle walls without creating chemical dependency.",
                    "dosage": "1 teaspoon (5g) at bedtime with warm water"
                },
                {
                    "name": "Panchasakar Churna (पञ्चसकार चूर्ण)",
                    "action": "Senna & Spices Cleansing Formula",
                    "details": "Swarnapatri, Haritaki, Shunthi, Saunf, and Saindhava; effectively flushes stubborn fecal matter.",
                    "dosage": "3-5 grams at bedtime with lukewarm water"
                },
                {
                    "name": "Abhayarishta (अभयारिष्ट)",
                    "action": "Classical Haritaki Ferment",
                    "details": "Corrects chronic sluggish bowels, abdominal gas distention, and relieves hemorrhoids.",
                    "dosage": "20ml with equal water twice daily after meals"
                },
                {
                    "name": "Erand Sneha (एरण्ड तैल / Castor Oil)",
                    "action": "Classical Lubricating Purgative",
                    "details": "Ricinus communis cold-pressed oil that lubricates dry Vata in the large intestine.",
                    "dosage": "10-15ml in a cup of warm milk at bedtime SOS"
                }
            ],
            "homeopathy": [
                {
                    "name": "Nux Vomica 30C",
                    "action": "Frequent Ineffectual Urging",
                    "details": "Constipation from sedentary life, rich food, or stress; sensation that part of stool remained behind.",
                    "dosage": "4 pills at bedtime"
                },
                {
                    "name": "Bryonia Alba 30C",
                    "action": "Dry Hard Burnt-Looking Stool",
                    "details": "Stool large, hard, extremely dry as if burnt; absence of intestinal moisture and secretions.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Alumina 30C",
                    "action": "Complete Inactivity of Rectum",
                    "details": "No desire for stool for days; even soft stool adheres to rectal wall and requires great straining.",
                    "dosage": "4 pills twice daily"
                },
                {
                    "name": "Cascara Sagrada Q (Mother Tincture)",
                    "action": "Tonic Laxative Tincture",
                    "details": "Restores tone to sluggish intestinal muscularis without griping.",
                    "dosage": "15 drops in water at bedtime"
                }
            ]
        }
    },
    {
        "keywords": ["insomnia", "sleep", "sleeplessness", "anxiety", "panic", "stress", "nidranasha", "manas roga"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Melatonin 3mg / 5mg",
                    "action": "Circadian Rhythm Regulator",
                    "details": "Pineal receptor agonist that normalizes sleep-wake cycle without dependence or daytime hangover.",
                    "dosage": "3-5mg orally 30-60 minutes before scheduled bedtime"
                },
                {
                    "name": "Tab. Zolpidem 5mg / 10mg",
                    "action": "Non-Benzodiazepine GABA-A Hypnotic",
                    "details": "Fast-acting hypnotic for short-term treatment of sleep onset insomnia (Use under prescription).",
                    "dosage": "5-10mg immediately before getting into bed"
                },
                {
                    "name": "Tab. Clonazepam 0.25mg / 0.5mg",
                    "action": "Long-Acting Benzodiazepine Anxiolytic",
                    "details": "Calms generalized somatic anxiety, panic attacks, and restless leg nocturnal agitation.",
                    "dosage": "0.25mg-0.5mg at bedtime as advised by physician"
                },
                {
                    "name": "Tab. Escitalopram 10mg",
                    "action": "Selective Serotonin Reuptake Inhibitor (SSRI)",
                    "details": "Evidence-based therapy for generalized anxiety disorder, panic disorder, and depressive sleep disruption.",
                    "dosage": "10mg once daily in the morning"
                }
            ],
            "ayurveda": [
                {
                    "name": "Ashwagandha Churna / Capsules (अश्वगन्धा)",
                    "action": "Premier Adaptogenic Rasayana",
                    "details": "Withania somnifera lowers serum cortisol, counters mental exhaustion, and induces natural deep sleep.",
                    "dosage": "1 capsule (500mg) or 3g powder twice daily with warm milk"
                },
                {
                    "name": "Brahmi Vati / Saraswatarishta (ब्राह्मी)",
                    "action": "Medhya Rasayana & Gold Compound",
                    "details": "Bacopa monnieri compound that nourishes cerebral neurons, improves concentration, and pacifies anxiety.",
                    "dosage": "1 tablet twice daily or 15ml Saraswatarishta after meals"
                },
                {
                    "name": "Tagar (तगर / Valeriana wallichii)",
                    "action": "Natural Sedative Botanical",
                    "details": "Potent valepotriate-rich root extract that calms central nervous agitation and cures Nidranasha.",
                    "dosage": "1 capsule (250mg) at bedtime with warm water"
                },
                {
                    "name": "Shankhpushpi Syrup (शंखपुष्पी)",
                    "action": "Neuro-Cognitive Calming Tonic",
                    "details": "Convolvulus pluricaulis formulation that relieves psychosomatic tension and restlessness.",
                    "dosage": "10-15ml twice daily after food"
                }
            ],
            "homeopathy": [
                {
                    "name": "Coffea Cruda 30C",
                    "action": "Wide-Awake Rush of Thoughts",
                    "details": "Sleeplessness from mental overactivity, rapid flow of creative ideas, good news, or excitement.",
                    "dosage": "4 pills at bedtime"
                },
                {
                    "name": "Passiflora Incarnata Q (Mother Tincture)",
                    "action": "Natural Herbal Sleep Inducer",
                    "details": "Passion flower tincture that produces quiet, restful natural sleep without narcotic hangover.",
                    "dosage": "15-20 drops in half a cup of warm water 30 minutes before bed"
                },
                {
                    "name": "Kali Phosphoricum 6X",
                    "action": "Biochemic Nerve Nutrient",
                    "details": "Relieves brain-fag, nervous dread, weakness after mental exertion, and insomnia from worry.",
                    "dosage": "4 tablets dissolved on tongue 3 times daily"
                },
                {
                    "name": "Ignatia Amara 30C",
                    "action": "Grief, Shock & Emotional Stress",
                    "details": "Insomnia following emotional bereavement, sudden shock, heartbreak, or involuntary sighing.",
                    "dosage": "4 pills twice daily"
                }
            ]
        }
    },
    {
        "keywords": ["uti", "urinary tract infection", "dysuria", "burning urine", "mutrakrichhra", "mutraghata", "cystitis", "ashmari"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Nitrofurantoin 100mg (Controlled Release)",
                    "action": "Urinary Antibacterial",
                    "details": "Concentrates rapidly in bladder urine to eradicate uropathogenic E. coli with minimal bowel disruption.",
                    "dosage": "100mg twice daily with meals for 5 days"
                },
                {
                    "name": "Sachet Fosfomycin Trometamol 3g",
                    "action": "Single-Dose Broad-Spectrum Agent",
                    "details": "Rapid, single-dose oral solution providing sustained therapeutic urinary levels for 72 hours.",
                    "dosage": "1 sachet (3g) dissolved in half glass of water on empty stomach at bedtime"
                },
                {
                    "name": "Syrup Disodium Hydrogen Citrate (Citro-Soda)",
                    "action": "Systemic Urine Alkalizer",
                    "details": "Raises urinary pH, terminating burning sensations during micturition and inhibiting bacterial growth.",
                    "dosage": "15ml mixed in full glass of water 3 times daily"
                },
                {
                    "name": "Cranberry Extract 500mg + D-Mannose Tablets",
                    "action": "Anti-Adherence Prophylaxis",
                    "details": "Proanthocyanidins prevent E. coli type 1 fimbriae from adhering to bladder uroepithelium.",
                    "dosage": "1 tablet twice daily with water"
                }
            ],
            "ayurveda": [
                {
                    "name": "Gokshuradi Guggulu (गोक्षुरादि गुग्गुलु)",
                    "action": "Premier Classical Diuretic & Lithotriptic",
                    "details": "Tribulus terrestris and Commiphora mukul; clears burning dysuria, cleanses urinary channels, and flushes sediment.",
                    "dosage": "2 tablets twice daily with warm water or Punarnavashtak Kwath"
                },
                {
                    "name": "Chandanasava (चन्दनासव)",
                    "action": "Sandalwood Cooling Tonic",
                    "details": "White sandalwood and cooling herbs that instantly pacify burning micturition (Mutrakrichhra).",
                    "dosage": "15-20ml with equal water twice daily after meals"
                },
                {
                    "name": "Chandraprabha Vati (चन्द्रप्रभावटी)",
                    "action": "Genitourinary Tonic",
                    "details": "Eliminates pus cells, reduces urinary frequency, and strengthens bladder sphincter tone.",
                    "dosage": "1-2 tablets twice daily after food"
                },
                {
                    "name": "Punarnavashtak Kwath (पुनर्नवाष्टक क्वाथ)",
                    "action": "Renal & Urinary Flusher",
                    "details": "Boerhavia diffusa decoction that relieves inflammatory edema and promotes copious clear urine flow.",
                    "dosage": "20ml with equal water twice daily before meals"
                }
            ],
            "homeopathy": [
                {
                    "name": "Cantharis 30C",
                    "action": "Violent Burning & Cutting Dysuria",
                    "details": "Unbearable cutting burning pains before, during, and after urination; constant intolerable urge with scalding drops.",
                    "dosage": "4 pills every 1-2 hours in acute phase, then 3 times daily"
                },
                {
                    "name": "Sarsaparilla 30C",
                    "action": "Severe Pain at Close of Urination",
                    "details": "Excruciating pain specifically as the last drops pass; gravel or white sand in urine.",
                    "dosage": "4 pills 3 times daily"
                },
                {
                    "name": "Berberis Vulgaris Q / 30C",
                    "action": "Radiating Renal & Ureteral Pain",
                    "details": "Bubbling sensation in lumbar kidney region radiating down ureters to bladder and urethra.",
                    "dosage": "10 drops in water or 4 pills 3 times daily"
                },
                {
                    "name": "Uva Ursi Q (Mother Tincture)",
                    "action": "Botanical Urinary Antiseptic",
                    "details": "Indicated in cystitis with blood and mucus in urine, painful tenesmus, and burning.",
                    "dosage": "10 drops in warm water thrice daily"
                }
            ]
        }
    },
    {
        "keywords": ["paracetamol", "acetaminophen", "dolo", "crocin", "calpol"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Paracetamol 650mg (Dolo / Crocin / Calpol)",
                    "action": "Centrally Acting Antipyretic & Analgesic",
                    "details": "First-line medicine for fever reduction and mild-to-moderate pain relief.",
                    "dosage": "650mg orally every 4-6 hours SOS after meals (Max 4g/day)"
                }
            ],
            "ayurveda": [
                {
                    "name": "Sudarshan Vati (सुदर्शन वटी)",
                    "action": "Natural Antipyretic Equivalent",
                    "details": "Classical bitter polyherbal formula providing systemic fever and pain relief.",
                    "dosage": "1-2 tablets twice daily with warm water"
                },
                {
                    "name": "Giloy Ghanvati (गिलोय घनवटी)",
                    "action": "Antipyretic & Rasayana",
                    "details": "Extract of Tinospora cordifolia that clears toxins and reduces bodily pain.",
                    "dosage": "1 tablet twice daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Aconitum Napellus 30C",
                    "action": "Acute Febrile Onset",
                    "details": "Indicated for sudden fever with body ache and restlessness.",
                    "dosage": "4 pills 3-4 times daily"
                },
                {
                    "name": "Belladonna 30C",
                    "action": "Congestive Heat & Throbbing",
                    "details": "High fever, flushed face, and burning body heat.",
                    "dosage": "4 pills 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["metformin", "glycomet"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Metformin 500mg / 1000mg (Glycomet)",
                    "action": "Biguanide Insulin Sensitizer",
                    "details": "Reduces hepatic glucose output and improves peripheral glucose uptake.",
                    "dosage": "500mg twice daily with meals"
                }
            ],
            "ayurveda": [
                {
                    "name": "Chandraprabha Vati (चन्द्रप्रभावटी)",
                    "action": "Prameha Metabolic Regulator",
                    "details": "Clears urinary sediment and improves cellular glucose sensitivity.",
                    "dosage": "2 tablets twice daily with water"
                },
                {
                    "name": "Nishamalaki Churna (निशामलकी)",
                    "action": "Haridra + Amla Compound",
                    "details": "Antioxidant formula that protects microcirculation and stabilizes blood sugar.",
                    "dosage": "3 grams twice daily before meals"
                }
            ],
            "homeopathy": [
                {
                    "name": "Syzygium Jambolanum Q (Mother Tincture)",
                    "action": "Pancreatic Glycosuria Regulator",
                    "details": "10-15 drops in water thrice daily before meals to lower blood sugar.",
                    "dosage": "10 drops in water 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["amlodipine", "norvasc", "stamlo"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Amlodipine 5mg (Stamlo / Norvasc)",
                    "action": "Dihydropyridine Calcium Channel Blocker",
                    "details": "Relaxes arterial smooth muscle to lower elevated blood pressure.",
                    "dosage": "5mg once daily in morning"
                }
            ],
            "ayurveda": [
                {
                    "name": "Sarpagandha Ghanvati (सर्पगंधा घनवटी)",
                    "action": "Natural Reserpine Hypotensive",
                    "details": "Classical Rauwolfia root extract that calms arterial pressure.",
                    "dosage": "1 tablet at bedtime with warm water"
                },
                {
                    "name": "Mukta Vati (मुक्ता वटी)",
                    "action": "Pearl Compound",
                    "details": "Maintains healthy blood pressure and relieves stress.",
                    "dosage": "1 tablet twice daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Rauwolfia Serpentina Q (Mother Tincture)",
                    "action": "Homeopathic Hypotensive",
                    "details": "10 drops in water twice daily after meals to stabilize blood pressure.",
                    "dosage": "10 drops in water twice daily"
                }
            ]
        }
    },
    {
        "keywords": ["ashwagandha", "withania somnifera"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Tab. Melatonin 3mg + Vitamin B-Complex with Zinc",
                    "action": "Neuro-Restorative & Adaptogenic Support",
                    "details": "Counters physical and nervous fatigue, restoring sleep-wake rhythm.",
                    "dosage": "1 tablet at bedtime"
                }
            ],
            "ayurveda": [
                {
                    "name": "Ashwagandha Churna / Capsules (Withania somnifera)",
                    "action": "Premier Adaptogenic Rasayana",
                    "details": "Builds Ojas, reduces cortisol, and strengthens muscle and nervous tone.",
                    "dosage": "1 capsule (500mg) or 3g powder twice daily with warm milk"
                }
            ],
            "homeopathy": [
                {
                    "name": "Withania Somnifera Q (Mother Tincture)",
                    "action": "Nervine Adaptogen",
                    "details": "Relieves brain-fag, sexual debility, and mental exhaustion.",
                    "dosage": "10-15 drops in water twice daily"
                },
                {
                    "name": "Kali Phosphoricum 6X",
                    "action": "Nerve Tissue Nutrient",
                    "details": "Biochemic tissue salt for nervous prostration and exhaustion.",
                    "dosage": "4 tablets 3 times daily"
                }
            ]
        }
    },
    {
        "keywords": ["arnica", "arnica montana"],
        "medicines": {
            "allopathy": [
                {
                    "name": "Topical Diclofenac Gel 1% / 2%",
                    "action": "Topical NSAID Analgesic",
                    "details": "Relieves muscle soreness, sprains, bruises, and joint pain.",
                    "dosage": "Apply over painful area 3-4 times daily"
                },
                {
                    "name": "Tab. Paracetamol 650mg",
                    "action": "Systemic Analgesic",
                    "details": "For blunt trauma body aches and muscle contusions.",
                    "dosage": "650mg after meals SOS"
                }
            ],
            "ayurveda": [
                {
                    "name": "Murivenna Taila (मुरिवेण्णा तैल)",
                    "action": "Classical Wound & Sprain Healing Oil",
                    "details": "Formulated with Betel leaf, Aloe, and Karanja; rapidly heals sprains, fractures, and bruises.",
                    "dosage": "Apply warm oil over injured muscle or joint"
                },
                {
                    "name": "Mahanarayan Taila (महानारायण तैल)",
                    "action": "Musculoskeletal Massage Oil",
                    "details": "Relieves deep aching pain and stiffness in muscles and joints.",
                    "dosage": "Gentle massage twice daily"
                }
            ],
            "homeopathy": [
                {
                    "name": "Arnica Montana 30C / 200C",
                    "action": "Sovereign Trauma & Bruise Remedy",
                    "details": "First remedy for falls, blows, contusions, muscular strain, and bruised aching sensation.",
                    "dosage": "4 pills every 2-3 hours after injury, then twice daily"
                }
            ]
        }
    }
]


def normalize_medicine_lookup_text(text: str) -> str:
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower()).strip()


def get_prescribed_medicines_for_term(term: str) -> Dict[str, List[Dict[str, Any]]]:
    clean = normalize_medicine_lookup_text(term)
    if not clean:
        return {"allopathy": [], "ayurveda": [], "homeopathy": []}

    clean_words = set(clean.split())
    best_match = None
    best_score = 0

    for entry in PRESCRIBED_MEDICINES_DATA:
        score = 0
        for kw in entry["keywords"]:
            kw_clean = normalize_medicine_lookup_text(kw)
            if clean == kw_clean:
                score = max(score, 100 + len(kw_clean))
            elif kw_clean in clean:
                score = max(score, 50 + len(kw_clean))
            else:
                kw_words = set(kw_clean.split())
                overlap = clean_words.intersection(kw_words)
                if overlap:
                    score = max(score, len(overlap) * 10)

        if score > best_score:
            best_score = score
            best_match = entry["medicines"]

    result: Dict[str, List[Dict[str, Any]]] = {"allopathy": [], "ayurveda": [], "homeopathy": []}
    if best_match:
        for k in ["allopathy", "ayurveda", "homeopathy"]:
            result[k] = list(best_match.get(k, []))

    # Fallback to search_concepts in knowledge_base.db for monograph medicines
    for sys_key in ["allopathy", "ayurveda", "homeopathy"]:
        if not result[sys_key]:
            try:
                db_meds = knowledge_db.search_concepts(
                    query=term,
                    medical_system=sys_key,
                    concept_type="monograph_medicine",
                    limit=4
                )
                if db_meds:
                    result[sys_key] = [
                        {
                            "name": m.get("term", ""),
                            "action": f"{sys_key.capitalize()} Pharmacopoeia Monograph ({m.get('code', '')})",
                            "details": m.get("definition") or "Official pharmacopoeial medicinal product.",
                            "dosage": "Administer according to registered pharmacopoeia specifications."
                        }
                        for m in db_meds
                    ]
            except Exception:
                pass

    return result


def compare_systems(term_or_code: str) -> Dict[str, Any]:
    """
    Cross-system comparison: queries Allopathy, Ayurveda, and Homeopathy simultaneously.
    Identifies available official concepts, retrieves prescribed clinical medicines for each system,
    and highlights systems where no records exist.
    """
    clean_term = term_or_code.strip()
    if not clean_term:
        return {
            "query": "",
            "allopathy": [],
            "ayurveda": [],
            "homeopathy": [],
            "prescribed_medicines": {
                "allopathy": [],
                "ayurveda": [],
                "homeopathy": []
            },
            "summary": {
                "allopathy_matches": 0,
                "ayurveda_matches": 0,
                "homeopathy_matches": 0
            },
            "disclaimer": "Please provide a medical term or code to compare."
        }

    comparison = knowledge_db.compare_across_systems(clean_term)
    prescribed_medicines = get_prescribed_medicines_for_term(clean_term)

    # Attach prescribed medicines directly to each concept
    for sys_key in ["allopathy", "ayurveda", "homeopathy"]:
        sys_meds = prescribed_medicines.get(sys_key, [])
        for concept in comparison.get(sys_key, []):
            c_term = concept.get("term", "")
            c_meds = get_prescribed_medicines_for_term(c_term).get(sys_key, [])
            if c_meds:
                concept["prescribed_medicines"] = c_meds
            elif sys_meds:
                concept["prescribed_medicines"] = sys_meds
            else:
                concept["prescribed_medicines"] = []

    summary = {
        "allopathy_matches": len(comparison["allopathy"]),
        "ayurveda_matches": len(comparison["ayurveda"]),
        "homeopathy_matches": len(comparison["homeopathy"]),
        "prescribed_medicines_count": {
            "allopathy": len(prescribed_medicines.get("allopathy", [])),
            "ayurveda": len(prescribed_medicines.get("ayurveda", [])),
            "homeopathy": len(prescribed_medicines.get("homeopathy", []))
        },
        "systems_with_data": [
            sys for sys, items in [
                ("Allopathy (SNOMED CT)", comparison["allopathy"]),
                ("Ayurveda (NAMASTE SAT)", comparison["ayurveda"]),
                ("Homeopathy (ICD-10 / PCIM&H)", comparison["homeopathy"])
            ] if len(items) > 0
        ],
        "systems_without_data": [
            sys for sys, items in [
                ("Allopathy (SNOMED CT)", comparison["allopathy"]),
                ("Ayurveda (NAMASTE SAT)", comparison["ayurveda"]),
                ("Homeopathy (ICD-10 / PCIM&H)", comparison["homeopathy"])
            ] if len(items) == 0
        ]
    }

    return {
        "query": clean_term,
        "allopathy": comparison["allopathy"],
        "ayurveda": comparison["ayurveda"],
        "homeopathy": comparison["homeopathy"],
        "prescribed_medicines": prescribed_medicines,
        "summary": summary,
        "disclaimer": (
            "Official terminology comparison for educational purposes only. "
            "Different medical paradigms describe health and disease using distinct "
            "frameworks; surface term matches do NOT prove clinical equivalence."
        )
    }


def generate_educational_comparison(
    term: str,
    comparative_data: Dict[str, Any],
    gemini_client: Any = None,
    model_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uses Open-Source Local AI (Ollama / Llama 3.2) to produce an educational explanation comparing
    the retrieved medical knowledge across Allopathy, Ayurveda, and Homeopathy.

    Strict Safety Guardrails:
    - Bases analysis ONLY on retrieved official data.
    - Never hallucinates medical codes, medicines, dosages, or treatments.
    - Explains exact matches, partial conceptual overlaps, and unavailable equivalents.
    - Explicitly emphasizes paradigm differences (e.g. Tridosha vs Cellular Pathology vs Law of Similars).
    - Refuses to claim clinical equivalence without formal clinical validation.
    """
    clean_term = term.strip()

    # Prepare structured summary of retrieved concepts to pass as grounded context
    def format_system_concepts(items: List[Dict[str, Any]]) -> str:
        if not items:
            return "No official records found for this query in this system."
        formatted = []
        for i, item in enumerate(items[:5], 1):
            syns = ", ".join([s["synonym"] for s in item.get("synonyms", [])[:4]]) or "None listed"
            formatted.append(
                f"{i}. Term: {item.get('term')}\n"
                f"   Official Code: {item.get('code')}\n"
                f"   Concept Type: {item.get('concept_type')}\n"
                f"   Definition/Context: {item.get('definition') or 'No definition in dataset'}\n"
                f"   Official Source: {item.get('source_name')} ({item.get('publisher')})\n"
                f"   Synonyms/Aliases: {syns}"
            )
        return "\n\n".join(formatted)

    def format_prescribed_meds(meds: List[Dict[str, Any]]) -> str:
        if not meds:
            return "No specific prescribed medicines mapped in dataset."
        return "\n".join([f"- {m.get('name')}: {m.get('action')} (Details: {m.get('details')}, Dosage: {m.get('dosage')})" for m in meds[:4]])

    prescribed_dict = comparative_data.get("prescribed_medicines", {})
    allopathy_meds_text = format_prescribed_meds(prescribed_dict.get("allopathy", []))
    ayurveda_meds_text = format_prescribed_meds(prescribed_dict.get("ayurveda", []))
    homeopathy_meds_text = format_prescribed_meds(prescribed_dict.get("homeopathy", []))

    allopathy_text = format_system_concepts(comparative_data.get("allopathy", []))
    ayurveda_text = format_system_concepts(comparative_data.get("ayurveda", []))
    homeopathy_text = format_system_concepts(comparative_data.get("homeopathy", []))

    prompt = f"""You are a medical informatics educator explaining cross-system medical terminology for the MedVeda educational platform.

User Query: "{clean_term}"

OFFICIAL RETRIEVED KNOWLEDGE BASE DATA:

[ALLOPATHY - SNOMED CT / BHTS]
{allopathy_text}

Prescribed Medicines & Clinical Formulations:
{allopathy_meds_text}

[AYURVEDA - NAMASTE PORTAL / CCRAS SAT]
{ayurveda_text}

Prescribed Medicines & Classical Formulations:
{ayurveda_meds_text}

[HOMEOPATHY - NAMASTE ICD-10 & PCIM&H HPI]
{homeopathy_text}

Prescribed Medicines & Pharmacopoeial Remedies:
{homeopathy_meds_text}

TASK:
Provide a structured, easy-to-understand educational comparison of the retrieved concepts using these exact sections:
1. Overview in Plain Language: Explain what the concept/term means in everyday language.
2. Cross-System Findings:
   - Allopathy Perspective (SNOMED CT): Mention the official code and clinical context.
   - Ayurveda Perspective (NAMASTE): Mention the Sanskrit/IAST terms, SAT code, and Ayurvedic conceptual understanding (dosha/dhatu context if available).
   - Homeopathy Perspective (NAMASTE/PCIM&H): Mention disease codes (ICD-10) and/or official pharmacopoeial monographs (HPI).
3. Overlap vs Differences:
   - Identify whether terms represent an exact name match, a partial conceptual overlap, or distinct paradigm perspectives.
   - Note which systems had no matching records.
4. Paradigm & Safety Warning:
   - Explain why matching terminology does NOT prove clinical equivalence.
   - Explain that each system operates on distinct diagnostic and therapeutic principles.
5. Official Source Citations: List the publishers and databases cited.

STRICT SAFETY RULES:
- Do NOT diagnose any illness or prescribe any medication, dosage, or regimen.
- Do NOT invent or hallucinate codes, medicines, or clinical claims not present in the data or established knowledge.
- Do NOT state or imply that any two terms or treatments are clinically interchangeable.
- State clearly when information is missing or when a system has no equivalent.
- Maintain an objective, educational tone appropriate for medical students and patients.
"""

    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    configured_model = os.getenv("OLLAMA_MODEL") or model_name or "llama3.2"

    candidate_models = [configured_model]
    for m in ["llama3.2", "mistral", "meditron", "biomistral", "llama3", "gemma2"]:
        if m not in candidate_models:
            candidate_models.append(m)

    explanation_text = None
    last_error = None
    used_model = configured_model

    for m_name in candidate_models:
        try:
            with httpx.Client(timeout=120.0) as client:
                res = client.post(
                    f"{ollama_base}/api/generate",
                    json={
                        "model": m_name,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    resp_text = data.get("response", "").strip()
                    if resp_text:
                        explanation_text = resp_text
                        used_model = m_name
                        break
                elif res.status_code == 404:
                    last_error = f"Model '{m_name}' not found in local Ollama installation."
                    continue
                else:
                    last_error = f"Ollama returned HTTP {res.status_code}: {res.text}"
        except httpx.ConnectError:
            return {
                "success": False,
                "error": (
                    "Could not connect to Ollama at http://localhost:11434. "
                    "Please ensure Ollama is installed and running on your laptop. "
                    "Run 'ollama run llama3.2' in PowerShell to start it."
                ),
                "educational_explanation": None
            }
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": (
                    "Ollama request timed out while generating explanation. "
                    "Try again or use a lighter model like 'llama3.2'."
                ),
                "educational_explanation": None
            }
        except Exception as e:
            last_error = str(e)
            continue

    if not explanation_text:
        return {
            "success": False,
            "error": (
                f"Ollama explanation failed: {last_error or 'No response received'}. "
                "Make sure an open model is downloaded in Ollama (e.g., 'ollama run llama3.2')."
            ),
            "educational_explanation": None
        }

    return {
        "success": True,
        "query": clean_term,
        "engine": f"Ollama ({used_model}) [100% Open-Source]",
        "educational_explanation": explanation_text,
        "disclaimer": (
            "Open-source AI-generated educational explanation based on official medical databases. "
            "Not intended for clinical diagnosis, treatment, or establishing clinical equivalence."
        )
    }

