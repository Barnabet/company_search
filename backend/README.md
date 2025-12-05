# Company Search API

API FastAPI pour l'extraction de critères de recherche d'entreprises françaises depuis des requêtes en langage naturel.

## 🚀 Déploiement sur Render

### Méthode 1 : Via le Dashboard Render

1. Créer un compte sur [Render](https://render.com)
2. Cliquer sur "New +" → "Web Service"
3. Connecter votre repository GitHub
4. Configurer :
   - **Name**: `company-search-api`
   - **Region**: Europe (Frankfurt)
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
5. Ajouter les variables d'environnement :
   - `OPENROUTER_API_KEY`: Votre clé API OpenRouter
   - `OPENROUTER_MODEL`: `google/gemini-2.5-flash-lite` (optionnel)
6. Cliquer sur "Create Web Service"

### Méthode 2 : Via render.yaml (Infrastructure as Code)

1. Pusher le fichier `render.yaml` à la racine du backend
2. Sur Render Dashboard, cliquer sur "New +" → "Blueprint"
3. Sélectionner votre repository
4. Render détectera automatiquement le `render.yaml`
5. Ajouter la variable d'environnement `OPENROUTER_API_KEY` (elle est marquée comme `sync: false` donc à ajouter manuellement)

## 🔧 Installation locale

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. Créer un fichier `.env` à partir de `.env.example` :
```bash
cp .env.example .env
```

3. Éditer `.env` et ajouter votre clé API OpenRouter

4. Lancer l'API :
```bash
uvicorn api:app --reload
```

L'API sera disponible sur `http://localhost:8000`

## 📚 Documentation API

Une fois l'API lancée, accéder à :
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🎯 Endpoints

### `GET /`
Health check de base

### `GET /health`
Vérification de la santé de l'API

### `POST /extract`
Extrait les critères de recherche depuis une requête en langage naturel.

**Request:**
```json
{
  "query": "Je cherche des PME en Ile-de-France dans la restauration avec un CA supérieur à 1M€"
}
```

**Response:**
```json
{
  "query": "Je cherche des PME en Ile-de-France dans la restauration avec un CA supérieur à 1M€",
  "result": {
    "localisation": {
      "present": true,
      "code_postal": null,
      "departement": null,
      "region": "Ile-de-France",
      "commune": null
    },
    "activite": {
      "present": true,
      "libelle_secteur": "Restauration",
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
}
```

## 🔑 Obtenir une clé API OpenRouter

1. Aller sur [OpenRouter](https://openrouter.ai/)
2. Créer un compte
3. Aller dans "API Keys"
4. Créer une nouvelle clé
5. Copier la clé et l'ajouter dans les variables d'environnement

## 📦 Structure

```
backend/
├── api.py                 # Application FastAPI principale
├── sector_matcher.py      # Matching des secteurs d'activité
├── data/
│   ├── libelle_secteur.txt
│   └── libelle_activite.txt
├── requirements.txt       # Dépendances Python
├── render.yaml           # Configuration Render
├── .env.example          # Template de configuration
└── README.md             # Ce fichier
```


