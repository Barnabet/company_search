"""
Script pour générer naf_mapping.json à partir du fichier XLS référentiel NAF.

Usage:
    python generate_naf_mapping.py
"""

import json
import sys
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
XLS_FILE = DATA_DIR / "referentiel-activites-france.xls"
OUTPUT_FILE = DATA_DIR / "naf_mapping.json"


def read_xls_file():
    """Lit le fichier XLS et retourne un DataFrame."""
    try:
        import pandas as pd
    except ImportError:
        print("❌ pandas n'est pas installé. Installez-le avec: pip install pandas openpyxl xlrd")
        sys.exit(1)
    
    if not XLS_FILE.exists():
        print(f"❌ Fichier XLS non trouvé: {XLS_FILE}")
        sys.exit(1)
    
    print(f"📖 Lecture du fichier: {XLS_FILE}")
    
    # D'abord, lister toutes les feuilles
    try:
        xls = pd.ExcelFile(XLS_FILE, engine='xlrd')
    except Exception:
        xls = pd.ExcelFile(XLS_FILE, engine='openpyxl')
    
    print(f"\n📋 Feuilles disponibles: {xls.sheet_names}")
    
    # Chercher la feuille avec les données NAF (la plus grande ou celle avec "NAF" dans le nom)
    best_sheet = None
    best_rows = 0
    
    for sheet_name in xls.sheet_names:
        df_temp = pd.read_excel(xls, sheet_name=sheet_name)
        print(f"   - '{sheet_name}': {len(df_temp)} lignes, {len(df_temp.columns)} colonnes")
        
        # Préférer les feuilles avec beaucoup de lignes
        if len(df_temp) > best_rows:
            best_rows = len(df_temp)
            best_sheet = sheet_name
    
    print(f"\n📖 Utilisation de la feuille: '{best_sheet}'")
    
    # Lire la feuille sélectionnée
    df = pd.read_excel(xls, sheet_name=best_sheet)
    
    # Si la première ligne ressemble à des headers mais n'est pas reconnue, ajuster
    # Chercher la ligne qui contient les vrais headers (souvent "Code" ou "NAF")
    header_row = None
    for i in range(min(20, len(df))):
        row_values = df.iloc[i].astype(str).str.lower()
        if any('code' in str(v) or 'naf' in str(v) or 'libel' in str(v) for v in row_values):
            header_row = i
            break
    
    if header_row is not None:
        print(f"   Headers trouvés à la ligne {header_row}")
        df = pd.read_excel(xls, sheet_name=best_sheet, header=header_row)
    
    print(f"✅ Fichier lu: {len(df)} lignes, {len(df.columns)} colonnes")
    print(f"   Colonnes: {list(df.columns)}")
    
    return df


def generate_mapping(df):
    """
    Génère le mapping activité -> codes NAF.
    
    Adapte cette fonction selon la structure réelle du fichier XLS.
    """
    import pandas as pd
    
    mapping = {}
    
    # Afficher un aperçu des données pour comprendre la structure
    print("\n📊 Aperçu des données:")
    print(df.head(10).to_string())
    print("\n")
    
    # Identifier les colonnes
    columns = df.columns.tolist()
    print(f"Colonnes disponibles: {columns}")
    
    # Colonnes spécifiques au référentiel NAF France
    naf_col = None
    libelle_col = None
    
    # Chercher les colonnes exactes
    for col in columns:
        col_str = str(col)
        if 'Code Activité' in col_str or 'code activité' in col_str.lower():
            naf_col = col
        elif 'Libellé Activite' in col_str or 'libellé activite' in col_str.lower():
            libelle_col = col
    
    # Fallback: chercher par mots-clés
    if naf_col is None or libelle_col is None:
        for col in columns:
            col_lower = str(col).lower()
            if naf_col is None and ('naf' in col_lower and 'code' in col_lower):
                naf_col = col
            if libelle_col is None and ('libel' in col_lower and 'activ' in col_lower):
                libelle_col = col
    
    print(f"\n🔍 Colonnes utilisées:")
    print(f"   Code NAF: {naf_col}")
    print(f"   Libellé: {libelle_col}")
    
    if naf_col is None or libelle_col is None:
        print("❌ Impossible d'identifier les colonnes. Vérifiez la structure du fichier.")
        return {}
    
    # Construire le mapping: libellé -> [codes NAF]
    for _, row in df.iterrows():
        code_naf = str(row[naf_col]).strip() if pd.notna(row[naf_col]) else ""
        libelle = str(row[libelle_col]).strip() if pd.notna(row[libelle_col]) else ""
        
        # Ignorer les lignes vides
        if not code_naf or not libelle or code_naf == 'nan' or libelle == 'nan':
            continue
        
        # Nettoyer le code NAF (garder format XXXXZ)
        code_naf = code_naf.replace(".", "").replace(" ", "").upper()
        
        # Ajouter au mapping
        if libelle not in mapping:
            mapping[libelle] = []
        
        if code_naf not in mapping[libelle]:
            mapping[libelle].append(code_naf)
    
    print(f"\n✅ Mapping généré: {len(mapping)} activités")
    
    return mapping


def save_mapping(mapping):
    """Sauvegarde le mapping en JSON."""
    # Trier par clé pour une meilleure lisibilité
    sorted_mapping = dict(sorted(mapping.items()))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted_mapping, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Mapping sauvegardé: {OUTPUT_FILE}")
    
    # Statistiques
    total_codes = sum(len(codes) for codes in mapping.values())
    print(f"\n📈 Statistiques:")
    print(f"   Activités: {len(mapping)}")
    print(f"   Codes NAF total: {total_codes}")
    print(f"   Moyenne codes/activité: {total_codes/len(mapping):.1f}")


def main():
    print("=" * 60)
    print("🏭 Générateur de NAF Mapping depuis XLS")
    print("=" * 60)
    
    # Importer pandas ici pour afficher l'erreur proprement
    try:
        import pandas as pd
    except ImportError:
        print("\n❌ pandas n'est pas installé.")
        print("   Installez les dépendances avec:")
        print("   pip install pandas xlrd openpyxl")
        sys.exit(1)
    
    # Lire le fichier XLS
    df = read_xls_file()
    
    # Générer le mapping
    mapping = generate_mapping(df)
    
    if not mapping:
        print("❌ Aucun mapping généré. Vérifiez la structure du fichier XLS.")
        sys.exit(1)
    
    # Sauvegarder
    save_mapping(mapping)
    
    print("\n✅ Terminé!")


if __name__ == "__main__":
    main()
