# inference_openrouter.py

import os
import json
from pathlib import Path
import requests
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sector_matcher import SectorMatcher, load_sectors


def load_env_from_file(env_path: Optional[str] = None, override: bool = True) -> None:
    """
    Charge les variables depuis un fichier .env (clé=valeur par ligne).
    Si override=True, écrase les variables existantes (priorité au .env local).
    Recherche d'abord le .env situé à côté de ce fichier, puis le chemin fourni.
    """
    candidate_paths = []
    module_dir = Path(__file__).resolve().parent
    candidate_paths.append(module_dir / ".env")
    if env_path:
        candidate_paths.insert(0, Path(env_path))
    candidate_paths.append(Path.cwd() / ".env")

    for path in candidate_paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key and (override or key not in os.environ):
                os.environ[key] = value
        break  # stop at the first .env found


# Assure que la clé locale définie dans .env prime sur les variables globales.
load_env_from_file()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Choisis le modèle que tu veux utiliser sur OpenRouter :
# ex : "openai/gpt-4o", "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", etc.
OPENROUTER_MODEL = "google/gemini-2.5-flash-lite"

# Initialize sector matcher for post-processing
_sector_matcher: Optional[SectorMatcher] = None

def get_sector_matcher() -> SectorMatcher:
    """Get or create the sector matcher singleton."""
    global _sector_matcher
    if _sector_matcher is None:
        _sector_matcher = SectorMatcher()
    return _sector_matcher

SYSTEM_PROMPT = """Tu es un extracteur de contraintes pour un moteur de recherche d'entreprises françaises.

TA MISSION
-----------
À partir d'une requête utilisateur en français (souvent très libre : "je cherche...", "trouve-moi...", "peux-tu", etc.),
tu dois détecter les critères décrits dans la requête et renvoyer UNIQUEMENT un objet JSON décrivant ces critères.

Tu ne dois jamais expliquer ta réponse, ni ajouter de texte autour.
Réponds toujours par UN SEUL objet JSON bien formé.

FORMAT DE SORTIE
----------------
Tu dois répondre avec exactement la structure suivante :

{
  "localisation": {
    "present": true/false,
    "code_postal": string ou null,
    "departement": string ou null,
    "region": string ou null,
    "commune": string ou null
  },
  "activite": {
    "present": true/false,
    "texte_activite": string ou null
  },
  "taille_entreprise": {
    "present": true/false,
    "tranche_effectif": string ou null,
    "acronyme": string ou null
  },
  "criteres_financiers": {
    "present": true/false,
    "ca_plus_recent": number ou null,
    "resultat_net_plus_recent": number ou null,
    "rentabilite_plus_recente": number ou null
  },
  "criteres_juridiques": {
    "present": true/false,
    "categorie_juridique": string ou null,
    "siege_entreprise": "oui" ou "non" ou null,
    "date_creation_entreprise": string ou null,
    "capital": number ou null,
    "date_changement_dirigeant": string ou null,
    "nombre_etablissements": number ou null
  }
}

RÈGLES GÉNÉRALES
----------------
- Tu dois toujours renvoyer un JSON valide :
  - guillemets doubles autour de toutes les clés et des valeurs de type string,
  - booleans en minuscules : true ou false,
  - null pour les champs inconnus / non déductibles.
- Si un critère n'est PAS demandé dans la requête, mets "present": false et tous les champs internes à null.
- Si un critère est clairement demandé (ou implique un filtrage), mets "present": true et remplis les champs que tu peux.
- Ne JAMAIS inventer des valeurs précises quand elles ne sont pas présentes dans la requête :
  - Si la requête ne mentionne pas de code NAF clair, ne fabrique pas de code : mets "activite_entreprise": null.
  - Si la requête ne donne pas de chiffre d'affaires, laisse les champs financiers à null.
  - Si la requête mentionne un département mais pas une région, laisse "region": null, ne cherche pas à déduire des valeurs pour des champs non précisés explicitement.
- Dates :
  - Utilise toujours le format "YYYY-MM-DD" (par exemple "2022-10-05").
  - Si la requête mentionne seulement une année ("créée en 2020"), mets "2020-01-01" (1er janvier de cette année).
- Nombres :
  - Retire les espaces, "€", "k", "K", "M" dans la sortie JSON.
  - Convertis "100 k€" en 100000, "1 M€" en 1000000, "1,5 M€" en 1500000 etc.
  - Pour les pourcentages, renvoie la valeur numérique sans "%". Exemple : "5,5 %" -> 5.5.

DÉTAIL DES CHAMPS
-----------------

1) Champ "localisation"
-----------------------
Ce champ sert à détecter si l'utilisateur impose un critère géographique.

"localisation.present" est true si la requête impose une contrainte de lieu :
- Mention d'une région : ex. "en Ile-de-France", "en Bretagne".
- Mention d'un département : ex. "dans le département 92", "dans les Hauts-de-Seine".
- Mention d'un code postal : ex. "autour de 92500", "75015".
- Mention d'une ville / commune interprétable comme localisation de l'entreprise.

"localisation.present" est false si :
- La requête ne parle pas du tout de localisation.
- La requête indique explicitement que la localisation n'est pas un critère : "peu importe la région", "sans filtre géographique".

- "code_postal" :
  - 5 chiffres sous forme de string (ex: "92500").
  - Si plusieurs codes postaux sont mentionnés, choisis le plus précis OU mets null si c'est vraiment une liste hétérogène.
  - Si la requête parle seulement d'un département ou d'une région, laisse "code_postal": null.

- "departement" :
  - Nom du département quand il est mentionné dans la requête, sinon null.
  - Par exemple : "HAUTS-DE-SEINE", "NORD", "GIRONDE"...
  - Si l'utilisateur donne un nombre pour le département, mets son nom correspondant (ex: "31" -> "HAUTE-GARONNE")
  - Si tu n'es pas sûr, laisse "departement": null.

- "region" :
  - Nom de région pris dans la liste suivante :
    - "Auvergne-Rhone-Alpes"
    - "Bourgogne-Franche-Comte"
    - "Bretagne"
    - "Centre-Val de Loire"
    - "Corse"
    - "Grand Est"
    - "Guadeloupe"
    - "Guyane"
    - "Hauts-de-France"
    - "Ile-de-France"
    - "La Réunion"
    - "Martinique"
    - "Mayotte"
    - "Normandie"
    - "Nouvelle Calédonie"
    - "Nouvelle-Aquitaine"
    - "Occitanie"
    - "Pays de la Loire"
    - "Polynésie Francaise"
    - "Provence-Alpes-Cote d'Azur"
    - "Saint-Martin"
    - "Saint-Pierre et Miquelon"
    - "Wallis et Futuna"
  - Remplis ce champ UNIQUEMENT si la région est EXPLICITEMENT mentionnée dans la requête.
  - INTERDICTION de déduire la région à partir du département ou de la ville. Si la requête dit "dans le 92" mais ne dit pas "Ile-de-France", "region" DOIT rester null.
  
- "commune" :
  - Nom de la commune si mentionné, sinon null.


2) Champ "activite"
-------------------
Ce champ décrit le secteur / activité de l'entreprise.

"activite.present" est true si la requête impose un critère d'activité :
- Mention d'un métier / secteur : "cabinet de conseil", "restauration", "industrie chimique", "bâtiment", "BTP", etc.
- Mention explicite d'un code NAF : "code NAF 6202A", "activités 56.10A".
- Mention d'un domaine d'activité précis : "cybersécurité", "agence digitale", "formation IA", etc.

"activite.present" est false si l'utilisateur ne donne aucun indice d'activité OU dit "toutes activités confondues".

- "libelle_secteur" :
  - Texte court qui résume le secteur. Essaie de reprendre EXACTEMENT les termes de la requête s'ils correspondent à une activité connue.
  - Évite de reformuler si possible. Exemple : si la requête dit "Restauration", garde "Restauration".
  - Si le secteur est très flou ("entreprises innovantes"), mets un libellé descriptif.
  - Si aucune information d'activité n'est donnée, "libelle_secteur": null.

- "activite_entreprise" :
  - Code NAF (ex: "6202A", "2512Z") UNIQUEMENT si la requête le donne explicitement.
  - INTERDICTION FORMELLE d'inventer ou de déduire un code NAF à partir du libellé. Même si tu es sûr que "Boulangerie" = "1071C", si l'utilisateur ne l'a pas écrit, mets "activite_entreprise": null.
  - Si l'utilisateur ne mentionne pas de code NAF, mets "activite_entreprise": null.

3) Champ "taille_entreprise"
----------------------------
Ce champ sert à capter la taille (effectifs) ou les acronymes TPE/PME/ETI/grand groupe.

"taille_entreprise.present" est true si :
- La requête parle du nombre de salariés : "moins de 10 salariés", "entre 50 et 200 salariés", etc.
- La requête mentionne des acronymes : "TPE", "PME", "ETI", "grand groupe".
- La requête demande explicitement une taille : "petites structures", "grands groupes".
- Le nombre d'établissements ne compte pas comme un critère de taille mais un critère juridique.

Sinon, "taille_entreprise.present" = false.

- "tranche_effectif" :
  - Doit être choisi dans la liste suivante (référentiel Sirene) :
    - "Unites non employeuses"
    - "pas de salaries"
    - "0 salarie"
    - "1 ou 2 salaries"
    - "3 a 5 salaries"
    - "6 a 9 salaries"
    - "10 a 19 salaries"
    - "20 a 49 salaries"
    - "50 a 99 salaries"
    - "100 a 199 salaries"
    - "200 a 249 salaries"
    - "250 a 499 salaries"
    - "500 a 999 salaries"
    - "1 000 a 1 999 salaries"
    - "2 000 a 4 999 salaries"
    - "5 000 a 9 999 salaries"
    - "10 000 salaries et plus"
  - Si l'utilisateur donne un intervalle de salariés (ex : "entre 20 et 50 salariés"), choisis la tranche qui correspond le mieux.
  - INTERDICTION de déduire une tranche à partir d'un acronyme. "Grand groupe" ne veut pas dire forcément "10 000 salaries et plus" pour toi.
  - Si c'est trop flou ("petites entreprises", "PME") sans nombre, laisse "tranche_effectif": null.

- "acronyme" :
  - "TPE", "PME", "ETI" ou "grand groupe".
  - Si l'utilisateur utilise ces termes, recopie-les tels quels.
  - Si tu n'as pas assez d'information, mets "acronyme": null.

4) Champ "criteres_financiers"
------------------------------
Ce champ capture les contraintes sur le chiffre d'affaires, le résultat net et la rentabilité.

"criteres_financiers.present" est true si la requête parle de CA, chiffre d'affaires, volume de ventes, résultat net,
profit, bénéfice, pertes, marge, rentabilité, etc.

Sinon, "criteres_financiers.present" = false.

- "ca_plus_recent" :
  - Chiffre d'affaires le plus récent mentionné ou le seuil demandé.
  - Exemples d'interprétation :
    - "CA supérieur à 1 M€" -> ca_plus_recent = 1000000
    - "chiffre d'affaires d'environ 500 k€" -> ca_plus_recent = 500000
    - "entre 1 et 5 M€" -> ca_plus_recent = 1000000 (borne basse de l'intervalle)
  - Si aucune info exploitable, mets null.

- "resultat_net_plus_recent" :
  - Même logique que pour le CA, mais pour le résultat net (bénéfice ou perte).
  - Si la requête est qualitative ("rentable", "en difficulté") sans montant chiffré, laisse ce champ à null.

- "rentabilite_plus_recente" :
  - Pourcentage de marge ou rentabilité.
  - Exemples :
    - "marge de 5 %" -> 5.0
    - "entre 3 et 8%" -> 3.0 (borne basse)
  - Si non précisée, null.

5) Champ "criteres_juridiques"
------------------------------
Ce champ sert à capter la forme juridique, le capital, la date de création et le nombre d'établissements.

"criteres_juridiques.present" est true si la requête impose au moins une contrainte de ce type :
- Forme juridique : "SA", "SARL", "SAS", "EURL", "micro-entreprise", "auto-entrepreneur", etc.
- Dates : "créées après 2020", "créées avant 2010", "créées en 2018".
- Capital social : "capital social supérieur à 10 000 €", etc.
- Nombre d'établissements : "au moins 3 établissements", "multi-sites", etc.
Sinon, "criteres_juridiques.present" = false.

- "categorie_juridique" :
  - Doit être choisi dans la liste suivante :
    - "Autre personne morale immatriculée au RCS"
    - "Entrepreneur individuel"
    - "Groupement de droit privé"
    - "Groupement de droit privé non doté de la personnalité morale"
    - "Organisme privé spécialisé"
    - "Personne morale de droit étranger"
    - "Personne morale de droit public soumise au droit commercial"
    - "Personne morale et organisme soumis au droit administratif"
    - "Société commerciale"
  - Règles de mapping simples :
    - SA, SAS, SASU, SARL, EURL, SNC, etc. => "Société commerciale"
    - micro-entreprise, auto-entrepreneur => "Entrepreneur individuel"
    - association loi 1901 => "Groupement de droit privé" (ou "Groupement de droit privé non doté de la personnalité morale")
  - INTERDICTION d'inventer une catégorie si l'utilisateur ne donne pas d'information juridique. Si la requête ne parle pas de forme juridique, mets "categorie_juridique": null.
  - Ne déduis pas la catégorie juridique à partir de l'activité. "Boulangerie" n'implique pas "Société commerciale" ni "Entrepreneur individuel" sans précision.

- "siege_entreprise" :
  - "oui" si la requête semble parler du siège social ou ne précise rien de particulier (par défaut).
  - "non" seulement si la requête mentionne explicitement les établissements secondaires, agences, magasins, etc.
  - Si doute, mets "oui".
  - Attention : Ce champ doit être rempli (oui/non) si "criteres_juridiques.present" est true. Si "criteres_juridiques.present" est false, tout doit être null.

- "date_creation_entreprise" :
  - Si la requête donne une date précise ("créée le 2020-10-22"), recopie-la telle quelle.
  - Si la requête donne une année ("créées en 2015"), mets "2015-01-01".
  - Si la requête dit "créées après 2018", mets la borne minimale "2018-01-01".
  - Sinon, null.

- "capital" :
  - Capital social minimal demandé (ou valeur indicative) en nombre.
  - "capital supérieur à 15 000 €" -> 15000
  - "capital d'au moins 1 M€" -> 1000000
  - Si aucune info, null.

- "date_changement_dirigeant" :
  - Date de changement de dirigeant si mentionnée explicitement.
  - Si seulement une année est indiquée, utilise "YYYY-01-01".
  - Sinon, null.

- "nombre_etablissements" :
  - Nombre minimal d'établissements si la requête est chiffrée.
  - "au moins 3 établissements" -> 3
  - "un seul établissement" -> 1
  - Si seulement "multi-établissements" ou "réseau de magasins" sans chiffre, laisse null.

EXEMPLES
--------
Exemple 1
Requête :
"Je cherche des PME de l'administration publique en Ile-de-France avec un chiffre d'affaires supérieur à 1 M€."

Réponse JSON attendue :
{
  "localisation": {
    "present": true,
    "code_postal": null,
    "departement": null,
    "region": "Ile-de-France",
    "commune": null
  },
  "activite": {
    "present": true,
    "libelle_secteur": "Administration publique et defense ; securite sociale obligatoire",
    "activite_entreprise": null
  },
  "taille_entreprise": {
    "present": true,
    "tranche_effectif": null,
    "acronyme": "PME"
  },
  "criteres_financiers": {
    "present": true,
    "ca_plus_recent": 1000000,
    "resultat_net_plus_recent": null,
    "rentabilite_plus_recente": null
  },
  "criteres_juridiques": {
    "present": false,
    "categorie_juridique": null,
    "siege_entreprise": null,
    "date_creation_entreprise": null,
    "capital": null,
    "date_changement_dirigeant": null,
    "nombre_etablissements": null
  }
}

Exemple 2
Requête :
"Donne-moi juste des informations générales sur les entreprises, sans filtre de localisation ni de secteur."

Réponse JSON attendue :
{
  "localisation": {
    "present": false,
    "code_postal": null,
    "departement": null,
    "region": null,
    "commune": null
  },
  "activite": {
    "present": false,
    "libelle_secteur": null,
    "activite_entreprise": null
  },
  "taille_entreprise": {
    "present": false,
    "tranche_effectif": null,
    "acronyme": null
  },
  "criteres_financiers": {
    "present": false,
    "ca_plus_recent": null,
    "resultat_net_plus_recent": null,
    "rentabilite_plus_recente": null
  },
  "criteres_juridiques": {
    "present": false,
    "categorie_juridique": null,
    "siege_entreprise": null,
    "date_creation_entreprise": null,
    "capital": null,
    "date_changement_dirigeant": null,
    "nombre_etablissements": null
  }
}

RAPPEL FINAL
------------
- Ta réponse doit être UN SEUL objet JSON, sans commentaire.
- Si une information n'est pas dans la requête, ne l'invente pas : mets null.
- Respecte strictement les noms de champs et la structure demandée.
"""

BATCH_SYSTEM_PROMPT = SYSTEM_PROMPT + """

MODE BATCH
----------
Tu dois traiter plusieurs requêtes à la fois et renvoyer un tableau JSON, dans le même ordre, où chaque entrée contient :
- "index": la position de la requête dans la liste fournie (0, 1, 2, ...)
- "extraction": l'objet JSON d'extraction qui suit EXACTEMENT la même structure, règles et formats décrits ci-dessus.

Sortie attendue (rien d'autre) :
[
  {
    "index": 0,
    "extraction": { ... structure identique au mode simple ... }
  },
  {
    "index": 1,
    "extraction": { ... }
  }
]

Respecte strictement les mêmes règles que pour une requête unique ; seule différence : plusieurs résultats dans un tableau.
"""


def _normalize_extraction_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Post-process extraction result to:
    1. Normalize libelle_secteur to exact reference values
    2. Enforce rules about null values based on 'present' flags
    3. Prevent inference of tranche_effectif from acronyme
    """
    if not isinstance(result, dict):
        return result
    
    # --- Normalize libelle_secteur ---
    activite = result.get("activite")
    if isinstance(activite, dict):
        libelle = activite.get("libelle_secteur")
        naf_code = activite.get("activite_entreprise")
        
        # If a NAF code is present and libelle_secteur is also set,
        # the model likely inferred the sector from the NAF code.
        # According to the rules, we should NOT infer sector from NAF code.
        # So nullify the sector in this case.
        if naf_code is not None and libelle is not None:
            # NAF code is set - sector was likely inferred, nullify it
            activite["libelle_secteur"] = None
        elif libelle is not None and isinstance(libelle, str):
            # No NAF code, just normalize the sector to reference values
            matcher = get_sector_matcher()
            matched = matcher.match(libelle, threshold=0.5)
            if matched:
                activite["libelle_secteur"] = matched
            # If no match found, keep the original value
    
    # --- Enforce criteres_juridiques rules ---
    # If criteres_juridiques.present is false, ALL fields must be null
    criteres_juridiques = result.get("criteres_juridiques")
    if isinstance(criteres_juridiques, dict):
        if criteres_juridiques.get("present") is False:
            # Set all fields to null when present is false
            criteres_juridiques["categorie_juridique"] = None
            criteres_juridiques["siege_entreprise"] = None
            criteres_juridiques["date_creation_entreprise"] = None
            criteres_juridiques["capital"] = None
            criteres_juridiques["date_changement_dirigeant"] = None
            criteres_juridiques["nombre_etablissements"] = None
    
    # --- Enforce taille_entreprise rules ---
    # Do NOT infer tranche_effectif from acronyme alone
    # If acronyme is set but no explicit tranche was requested, set tranche_effectif to null
    taille = result.get("taille_entreprise")
    if isinstance(taille, dict):
        acronyme = taille.get("acronyme")
        tranche = taille.get("tranche_effectif")
        # If we have an acronyme and the tranche looks like it was inferred from it, nullify
        # Common inferred patterns from acronymes:
        inferred_patterns = {
            "grand groupe": ["10 000 salaries et plus", "5 000 a 9 999 salaries"],
            "ETI": ["250 a 499 salaries", "500 a 999 salaries", "1 000 a 1 999 salaries"],
            "PME": ["10 a 19 salaries", "20 a 49 salaries", "50 a 99 salaries", "100 a 199 salaries", "200 a 249 salaries"],
            "TPE": ["0 salarie", "1 ou 2 salaries", "3 a 5 salaries", "6 a 9 salaries"],
        }
        if acronyme and tranche:
            # Check if tranche was likely inferred from acronyme
            for acro, typical_tranches in inferred_patterns.items():
                if acronyme.lower() == acro.lower() and tranche in typical_tranches:
                    # This looks like an inference - nullify it
                    taille["tranche_effectif"] = None
                    break
    
    return result


def _clean_json_content(content: str) -> str:
    """
    Nettoie la réponse textuelle du modèle (code fences, texte parasite) pour faciliter json.loads.
    """
    cleaned = content.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    # Tente d'extraire la partie entre le premier {/[ et le dernier }/]
    start_candidates = [idx for idx in (cleaned.find("{"), cleaned.find("[")) if idx != -1]
    if start_candidates:
        start = min(start_candidates)
        end_brace = cleaned.rfind("}")
        end_bracket = cleaned.rfind("]")
        end_candidates = [idx for idx in (end_brace, end_bracket) if idx != -1]
        if end_candidates:
            end = max(end_candidates)
            cleaned = cleaned[start : end + 1]

    return cleaned


class OpenRouterExtractorError(Exception):
    """Erreur personnalisée pour l'extraction des critères via OpenRouter."""


def build_payload(user_query: str) -> Dict[str, Any]:
    """
    Construit le payload pour l'appel OpenRouter.
    On utilise response_format: json_object pour forcer le modèle à renvoyer du JSON.
    Attention : tous les modèles ne supportent pas forcément ce paramètre.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    payload: Dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        # Si le modèle supporte les structured outputs, ceci force le JSON strict :
        "response_format": {"type": "json_object"},
        "temperature": 0.0,  # extraction => on veut du déterministe
    }
    return payload


def call_openrouter_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Appelle l'API OpenRouter et renvoie la réponse JSON brute."""
    if not OPENROUTER_API_KEY:
        raise OpenRouterExtractorError("OPENROUTER_API_KEY n'est pas définie dans les variables d'environnement.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Optionnel mais recommandé pour le ranking / attribution OpenRouter :
        # "HTTP-Referer": "https://ton-site-ou-ton-app.com",
        # "X-Title": "Nom de ton appli",
    }

    response = requests.post(
        url=OPENROUTER_API_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=60,
    )

    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        raise OpenRouterExtractorError(
            f"Erreur HTTP OpenRouter ({response.status_code}): {response.text}"
        ) from e

    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise OpenRouterExtractorError("Réponse OpenRouter non JSON.") from e


def extract_criteria(user_query: str) -> Dict[str, Any]:
    """
    Appelle OpenRouter avec le system prompt d'extraction et renvoie un dict Python
    correspondant à l'objet JSON renvoyé par le modèle.
    """
    payload = build_payload(user_query)
    raw = call_openrouter_chat(payload)

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise OpenRouterExtractorError(
            f"Format de réponse inattendu : {json.dumps(raw, ensure_ascii=False)}"
        ) from e

    # Normalement, grâce à response_format = json_object, "content" est déjà du JSON.
    # Mais au cas où, on parse explicitement.
    try:
        result = json.loads(_clean_json_content(content))
    except json.JSONDecodeError as e:
        raise OpenRouterExtractorError(
            f"Le modèle n'a pas renvoyé un JSON valide : {content}"
        ) from e

    # Post-process to normalize libelle_secteur to exact reference values
    result = _normalize_extraction_result(result)
    
    return result


def build_batch_payload(queries: List[str]) -> Dict[str, Any]:
    """
    Construit un payload unique pour traiter plusieurs requêtes dans un seul appel.
    On ne force pas response_format=json_object pour permettre un tableau en sortie.
    """
    user_lines = ["Liste des requêtes numérotées (garde l'ordre) :"]
    for idx, query in enumerate(queries):
        user_lines.append(f"{idx}: {query}")
    user_lines.append("Réponds avec un tableau JSON où chaque entrée contient l'index et l'extraction correspondante.")

    messages = [
        {"role": "system", "content": BATCH_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_lines)},
    ]

    payload: Dict[str, Any] = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.0,
    }
    return payload


def extract_batch(queries: List[str]) -> List[Dict[str, Any]]:
    """
    Traite plusieurs requêtes dans un seul appel modèle et renvoie une liste
    d'objets {"index": int, "extraction": dict}.
    """
    if not queries:
        return []

    payload = build_batch_payload(queries)
    raw = call_openrouter_chat(payload)

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise OpenRouterExtractorError(
            f"Format de réponse inattendu (batch) : {json.dumps(raw, ensure_ascii=False)}"
        ) from e

    try:
        parsed = json.loads(_clean_json_content(content))
    except json.JSONDecodeError as e:
        raise OpenRouterExtractorError(f"Le modèle n'a pas renvoyé un JSON valide (batch) : {content}") from e

    if not isinstance(parsed, list):
        raise OpenRouterExtractorError(f"Réponse batch inattendue (attendu une liste) : {parsed}")
    
    # Post-process each extraction result to normalize libelle_secteur
    for item in parsed:
        if isinstance(item, dict) and "extraction" in item:
            item["extraction"] = _normalize_extraction_result(item["extraction"])
    
    return parsed


def extract_batch_with_retries(queries: List[str], retries: int = 1) -> List[Dict[str, Any]]:
    """
    Tente plusieurs fois l'extraction batch avant de remonter l'erreur.
    """
    last_error: Optional[Exception] = None
    attempts = max(1, retries + 1)
    for _ in range(attempts):
        try:
            return extract_batch(queries)
        except OpenRouterExtractorError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    return extract_batch(queries)


class ExtractRequest(BaseModel):
    query: str


class ExtractResponse(BaseModel):
    query: str
    result: Dict[str, Any]


class BatchExtractRequest(BaseModel):
    queries: List[str]


class BatchExtractItem(BaseModel):
    query: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


app = FastAPI(
    title="OpenRouter Criteria Extractor",
    description="API pour extraire les critères métier depuis une requête utilisateur.",
)


@app.post("/extract", response_model=ExtractResponse)
def extract_endpoint(payload: ExtractRequest) -> ExtractResponse:
    try:
        result = extract_criteria(payload.query)
    except OpenRouterExtractorError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - FastAPI transforms to 500
        raise HTTPException(status_code=500, detail="Erreur inattendue lors de l'extraction.") from exc
    return ExtractResponse(query=payload.query, result=result)


@app.post("/extract/batch", response_model=List[BatchExtractItem])
def extract_batch_endpoint(payload: BatchExtractRequest) -> List[BatchExtractItem]:
    extracted_list: Optional[List[Dict[str, Any]]] = None
    batch_error: Optional[str] = None
    try:
        extracted_list = extract_batch_with_retries(payload.queries, retries=1)
    except OpenRouterExtractorError as exc:
        batch_error = str(exc)
    except Exception as exc:  # noqa: BLE001
        batch_error = f"Erreur inattendue lors du batch: {exc}"

    responses: List[BatchExtractItem] = []

    if extracted_list is None:
        # Fallback: traite chaque requête individuellement pour éviter les 502.
        for query in payload.queries:
            try:
                result = extract_criteria(query)
                responses.append(BatchExtractItem(query=query, result=result, error=None))
            except OpenRouterExtractorError as exc:
                responses.append(BatchExtractItem(query=query, result=None, error=str(exc)))
            except Exception:  # noqa: BLE001
                responses.append(BatchExtractItem(query=query, result=None, error=batch_error or "Erreur inattendue lors du fallback."))
        return responses

    # Map by index to preserve order and handle manquants.
    by_index = {}
    for item in extracted_list:
        idx = item.get("index")
        extraction = item.get("extraction")
        by_index[idx] = extraction

    for idx, query in enumerate(payload.queries):
        extraction = by_index.get(idx)
        if extraction is None:
            responses.append(BatchExtractItem(query=query, result=None, error=batch_error or "Extraction manquante dans la réponse batch."))
        else:
            responses.append(BatchExtractItem(query=query, result=extraction, error=None))
    return responses


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "inference_openrouter:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
