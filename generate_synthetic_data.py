
import json
import random
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# --- Configuration & Constants ---

OUTPUT_FILE = "synthetic_dataset.json"
DEFAULT_COUNT = 200

# Loaded from inference_openrouter.py logic
REGIONS = [
    "Auvergne-Rhone-Alpes", "Bourgogne-Franche-Comte", "Bretagne", "Centre-Val de Loire",
    "Corse", "Grand Est", "Guadeloupe", "Guyane", "Hauts-de-France", "Ile-de-France",
    "La Réunion", "Martinique", "Mayotte", "Normandie", "Nouvelle Calédonie",
    "Nouvelle-Aquitaine", "Occitanie", "Pays de la Loire", "Polynésie Francaise",
    "Provence-Alpes-Cote d'Azur", "Saint-Martin", "Saint-Pierre et Miquelon",
    "Wallis et Futuna"
]

# A sample of departments to use for generation
DEPARTEMENTS = [
    ("01", "AIN"), ("02", "AISNE"), ("03", "ALLIER"), ("06", "ALPES-MARITIMES"),
    ("13", "BOUCHES-DU-RHONE"), ("14", "CALVADOS"), ("21", "COTE-D'OR"),
    ("29", "FINISTERE"), ("31", "HAUTE-GARONNE"), ("33", "GIRONDE"),
    ("34", "HERAULT"), ("35", "ILLE-ET-VILAINE"), ("38", "ISERE"),
    ("44", "LOIRE-ATLANTIQUE"), ("45", "LOIRET"), ("57", "MOSELLE"),
    ("59", "NORD"), ("62", "PAS-DE-CALAIS"), ("67", "BAS-RHIN"),
    ("69", "RHONE"), ("75", "PARIS"), ("76", "SEINE-MARITIME"),
    ("77", "SEINE-ET-MARNE"), ("78", "YVELINES"), ("83", "VAR"),
    ("91", "ESSONNE"), ("92", "HAUTS-DE-SEINE"), ("93", "SEINE-SAINT-DENIS"),
    ("94", "VAL-DE-MARNE"), ("95", "VAL-D'OISE")
]

TRANCHES_EFFECTIF = [
    "Unites non employeuses", "pas de salaries", "0 salarie", "1 ou 2 salaries",
    "3 a 5 salaries", "6 a 9 salaries", "10 a 19 salaries", "20 a 49 salaries",
    "50 a 99 salaries", "100 a 199 salaries", "200 a 249 salaries",
    "250 a 499 salaries", "500 a 999 salaries", "1 000 a 1 999 salaries",
    "2 000 a 4 999 salaries", "5 000 a 9 999 salaries", "10 000 salaries et plus"
]

ACRONYMES_TAILLE = ["TPE", "PME", "ETI", "grand groupe"]

CATEGORIES_JURIDIQUES = [
    "Autre personne morale immatriculée au RCS",
    "Entrepreneur individuel",
    "Groupement de droit privé",
    "Société commerciale"
]

# Mapping some common terms to legal categories for generation
LEGAL_TERMS_MAP = {
    "Société commerciale": ["SA", "SARL", "SAS", "SASU", "EURL", "société commerciale"],
    "Entrepreneur individuel": ["micro-entreprise", "auto-entrepreneur", "indépendant", "freelance"],
    "Groupement de droit privé": ["association", "SCI"]
}

# Intro phrases to vary the structure
INTROS = [
    "Je cherche", "Trouve-moi", "Je veux la liste des", "Donne-moi les",
    "Sortir les", "Affichez les", "Recherche de", "Cible :", "Liste des",
    "Y a-t-il des", "Pourriez-vous trouver des", "Extraction des"
]

# Connectors
CONNECTORS = [" à ", " dans le ", " en ", " situées à ", " basées en ", " vers "]

# --- Load Data ---

def load_lines(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"Warning: {filepath} not found.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

ACTIVITES = load_lines("data/libelle_activite.txt")
SECTEURS = load_lines("data/libelle_secteur.txt")

# --- Generators ---

def generate_naive_naf():
    # Generate a fake NAF code format: 4 digits + 1 letter
    return f"{random.randint(1000, 9999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"

def base_json():
    """Returns the empty skeleton of the JSON output."""
    return {
        "localisation": {
            "present": False,
            "code_postal": None,
            "departement": None,
            "region": None
        },
        "activite": {
            "present": False,
            "libelle_secteur": None,
            "activite_entreprise": None
        },
        "taille_entreprise": {
            "present": False,
            "tranche_effectif": None,
            "acronyme": None
        },
        "criteres_financiers": {
            "present": False,
            "ca_plus_recent": None,
            "resultat_net_plus_recent": None,
            "rentabilite_plus_recente": None
        },
        "criteres_juridiques": {
            "present": False,
            "categorie_juridique": None,
            "siege_entreprise": None,
            "date_creation_entreprise": None,
            "capital": None,
            "date_changement_dirigeant": None,
            "nombre_etablissements": None
        }
    }

def gen_activity_query():
    """
    Template: [Intro] [Sector]
    Note: Only uses SECTEURS for libelle_secteur to ensure consistency with reference list.
    """
    # Only use SECTEURS for libelle_secteur field to ensure exact match with reference
    sector = random.choice(SECTEURS) if SECTEURS else None
    if not sector:
        raise ValueError("No sectors available")
    
    intro = random.choice(INTROS + [""])
    
    query = f"{intro} {sector}".strip()
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["libelle_secteur"] = sector
    
    return query, res

def gen_activity_location_region():
    """
    Template: [Activity] [Connector] [Region]
    """
    act = random.choice(SECTEURS)
    reg = random.choice(REGIONS)
    conn = random.choice(CONNECTORS)
    
    query = f"{act}{conn}{reg}"
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["libelle_secteur"] = act
    
    res["localisation"]["present"] = True
    res["localisation"]["region"] = reg
    
    return query, res

def gen_activity_location_dept():
    """
    Template: [Activity] [Connector] [Dept Name/Code]
    """
    act = random.choice(SECTEURS)
    dept_code, dept_name = random.choice(DEPARTEMENTS)
    
    # Randomly use code or name
    use_code = random.random() < 0.3
    dept_str = dept_code if use_code else dept_name
    
    # Improve natural language for numbers: "dans le 92", "dans l'Ain"
    conn = random.choice([" dans le ", " dans le département ", " vers "])
    if not use_code and dept_name[0] in "AEIOUY":
        conn = " dans l'"
    elif not use_code:
        conn = " dans le "
        
    query = f"{act}{conn}{dept_str}"
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["libelle_secteur"] = act
    
    res["localisation"]["present"] = True
    res["localisation"]["departement"] = dept_name # Always normalized name
    
    return query, res

def gen_naf_code_query():
    """
    Template: code NAF [Code]
    """
    code = generate_naive_naf()
    query = f"entreprises avec le code NAF {code}"
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["activite_entreprise"] = code
    
    return query, res

def gen_financial_ca():
    """
    Template: [Activity] avec CA > [Amount]
    """
    act = random.choice(SECTEURS)
    amount = random.choice([100, 500, 1000, 2000, 5000, 10000]) * 1000 # k€
    amount_str = f"{amount // 1000} k€" if random.random() < 0.5 else f"{amount} euros"
    if amount >= 1000000:
        amount_str = f"{amount/1000000} M€"
    
    op = random.choice(["supérieur à", "plus de", "au moins", "min"])
    
    query = f"{act} avec un chiffre d'affaires {op} {amount_str}"
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["libelle_secteur"] = act
    
    res["criteres_financiers"]["present"] = True
    res["criteres_financiers"]["ca_plus_recent"] = float(amount)
    
    return query, res

def gen_juridical_creation():
    """
    Template: [Activity] créée en [Year]
    """
    act = random.choice(SECTEURS)
    year = random.randint(1990, 2024)
    
    query = f"{act} créée en {year}"
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["libelle_secteur"] = act
    
    res["criteres_juridiques"]["present"] = True
    res["criteres_juridiques"]["siege_entreprise"] = "oui"  # Default when criteres_juridiques is present
    res["criteres_juridiques"]["date_creation_entreprise"] = f"{year}-01-01"
    
    return query, res

def gen_size_query():
    """
    Template: [Acronyme] [Activity] OR [Activity] [Tranche]
    """
    act = random.choice(SECTEURS)
    
    if random.random() < 0.5:
        # Acronym
        acro = random.choice(ACRONYMES_TAILLE)
        query = f"{acro} dans le secteur {act}"
        
        res = base_json()
        res["activite"]["present"] = True
        res["activite"]["libelle_secteur"] = act
        res["taille_entreprise"]["present"] = True
        res["taille_entreprise"]["acronyme"] = acro
    else:
        # Tranche
        tranche = random.choice(TRANCHES_EFFECTIF)
        # Map tranche back to natural language approx
        nl_tranche = tranche.replace("salaries", "salariés").replace("a ", "à ")
        
        query = f"{act} avec {nl_tranche}"
        
        res = base_json()
        res["activite"]["present"] = True
        res["activite"]["libelle_secteur"] = act
        res["taille_entreprise"]["present"] = True
        res["taille_entreprise"]["tranche_effectif"] = tranche
        
    return query, res

def gen_complex_query():
    """
    Combine multiple criteria.
    """
    act = random.choice(SECTEURS)
    reg = random.choice(REGIONS)
    acro = random.choice(ACRONYMES_TAILLE)
    
    parts = []
    parts.append(f"{acro}") # PME
    parts.append(f"{act}") # Informatique
    parts.append(f"en {reg}") # en Bretagne
    
    # Shuffle slightly? No, keep grammar somewhat sane.
    # "PME Informatique en Bretagne"
    query = f"{acro} {act} en {reg}"
    
    res = base_json()
    res["activite"]["present"] = True
    res["activite"]["libelle_secteur"] = act
    res["localisation"]["present"] = True
    res["localisation"]["region"] = reg
    res["taille_entreprise"]["present"] = True
    res["taille_entreprise"]["acronyme"] = acro
    
    # Maybe add financial
    if random.random() < 0.3:
        query += " avec plus de 2M€ de CA"
        res["criteres_financiers"]["present"] = True
        res["criteres_financiers"]["ca_plus_recent"] = 2000000.0

    return query, res


GENERATORS = [
    (gen_activity_query, 4),
    (gen_activity_location_region, 5),
    (gen_activity_location_dept, 5),
    (gen_naf_code_query, 1),
    (gen_financial_ca, 2),
    (gen_juridical_creation, 2),
    (gen_size_query, 3),
    (gen_complex_query, 3)
]

def generate_dataset(count=100):
    dataset = []
    seen_queries = set()
    
    # Normalize weights
    total_weight = sum(w for _, w in GENERATORS)
    
    print(f"Generating {count} unique samples...")
    
    attempts = 0
    while len(dataset) < count:
        attempts += 1
        if attempts > count * 5 and len(dataset) < count:
            print("Warning: Difficulty generating unique samples. Stopping early.")
            break
            
        # Select generator based on weights
        r = random.uniform(0, total_weight)
        upto = 0
        gen_func = GENERATORS[0][0]
        for func, weight in GENERATORS:
            if upto + weight >= r:
                gen_func = func
                break
            upto += weight
            
        try:
            query, result = gen_func()
        except Exception:
            # Fallback if random choice fails (empty lists etc)
            continue
            
        if query in seen_queries:
            continue
            
        seen_queries.add(query)
        dataset.append({
            "input": query,
            "expected_output": result
        })
        
        if len(dataset) % 1000 == 0:
            print(f"Generated {len(dataset)} samples...")
            
    return dataset

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic dataset for entity extraction.")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of samples to generate")
    args = parser.parse_args()
    
    data = generate_dataset(args.count)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully generated {len(data)} samples in {OUTPUT_FILE}")

