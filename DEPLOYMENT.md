# 📦 Guide de Déploiement Complet

Ce guide détaille toutes les étapes pour déployer l'application Company Search en production.

## 📋 Checklist avant déploiement

- [ ] Code pushé sur GitHub
- [ ] Clé API OpenRouter obtenue
- [ ] Compte Render créé
- [ ] Compte Vercel créé

## 🎯 Étape 1 : Déployer le Backend sur Render

### Option A : Via Dashboard (Recommandé pour débuter)

1. **Connexion à Render**
   - Aller sur https://render.com
   - Se connecter avec GitHub

2. **Créer un nouveau Web Service**
   - Dashboard → "New +" → "Web Service"
   - Sélectionner votre repository : `company_search`
   - Cliquer sur "Connect"

3. **Configuration du service**
   
   **Basic Settings** :
   - **Name** : `company-search-api` (ou votre choix)
   - **Region** : Europe (Frankfurt) - Plus proche de la France
   - **Branch** : `main` ou `master`
   - **Root Directory** : `backend`
   - **Runtime** : Python 3

   **Build & Deploy** :
   - **Build Command** : 
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command** :
     ```bash
     uvicorn api:app --host 0.0.0.0 --port $PORT
     ```

4. **Variables d'environnement**
   
   Section "Environment Variables" :
   - Cliquer sur "Add Environment Variable"
   - Ajouter :
     ```
     Key: OPENROUTER_API_KEY
     Value: [Votre clé API OpenRouter]
     ```
   - Optionnel :
     ```
     Key: OPENROUTER_MODEL
     Value: google/gemini-2.5-flash-lite
     ```

5. **Plan tarifaire**
   - Sélectionner "Free" pour commencer
   - Note : Le plan free s'endort après 15 min d'inactivité

6. **Créer le service**
   - Cliquer sur "Create Web Service"
   - Attendre le déploiement (2-5 minutes)
   - Le premier build peut prendre plus de temps

7. **Vérifier le déploiement**
   - Une fois "Live", cliquer sur l'URL (ex: `https://company-search-api.onrender.com`)
   - Vous devriez voir : `{"status":"ok","message":"Company Search Criteria Extractor API","version":"1.0.0"}`
   - Tester la doc : `https://company-search-api.onrender.com/docs`

8. **Copier l'URL**
   - Copier l'URL complète (sans `/` à la fin)
   - Exemple : `https://company-search-api.onrender.com`
   - Vous en aurez besoin pour le frontend

### Option B : Via render.yaml (Infrastructure as Code)

Si vous préférez une approche "infrastructure as code" :

1. Le fichier `backend/render.yaml` est déjà configuré
2. Dashboard Render → "New +" → "Blueprint"
3. Sélectionner votre repository
4. Render détecte le `render.yaml`
5. Ajouter manuellement `OPENROUTER_API_KEY` (marqué `sync: false`)
6. Déployer

### Obtenir une clé API OpenRouter

1. Aller sur https://openrouter.ai/
2. Cliquer sur "Sign Up" / "Sign In"
3. Une fois connecté, aller dans "API Keys"
4. Cliquer sur "Create API Key"
5. Donner un nom : "Company Search Production"
6. Copier la clé (elle ne sera plus visible après)
7. Ajouter des crédits si nécessaire (le modèle Gemini est très économique)

### Troubleshooting Backend

**Erreur : "Application failed to respond"**
- Vérifier les logs dans l'onglet "Logs"
- S'assurer que `OPENROUTER_API_KEY` est définie
- Vérifier que le Start Command est correct

**Erreur : "No module named 'fastapi'"**
- Vérifier que `requirements.txt` est bien dans `backend/`
- Vérifier le Build Command

**Le service s'endort**
- C'est normal avec le plan gratuit
- Le premier appel après réveil prend ~30s
- Passer au plan payant pour éviter ça

## 🎯 Étape 2 : Déployer le Frontend sur Vercel

### Via Dashboard Vercel (Recommandé)

1. **Connexion à Vercel**
   - Aller sur https://vercel.com
   - Se connecter avec GitHub

2. **Importer le projet**
   - Dashboard → "Add New..." → "Project"
   - Sélectionner votre repository `company_search`
   - Cliquer sur "Import"

3. **Configuration du projet**
   
   **Project Settings** :
   - **Project Name** : `company-search-frontend` (ou votre choix)
   - **Framework Preset** : Next.js (détection automatique)
   - **Root Directory** : `frontend`
   - **Build Command** : `npm run build` (détection auto)
   - **Output Directory** : `.next` (détection auto)
   - **Install Command** : `npm install` (détection auto)

4. **Variables d'environnement**
   
   Section "Environment Variables" :
   - Cliquer sur "Add New"
   - Ajouter :
     ```
     Key: NEXT_PUBLIC_API_URL
     Value: https://company-search-api.onrender.com
     ```
   - ⚠️ Remplacer par VOTRE URL Render de l'étape 1
   - ⚠️ Pas de `/` à la fin !
   - Environnement : "Production" (cocher)

5. **Déployer**
   - Cliquer sur "Deploy"
   - Attendre le déploiement (1-3 minutes)

6. **Vérifier le déploiement**
   - Une fois "Ready", cliquer sur "Visit"
   - Vous devriez voir l'interface Company Search
   - Tester une requête pour vérifier la connexion API

7. **Copier l'URL**
   - L'URL est : `https://[project-name].vercel.app`
   - Exemple : `https://company-search-frontend.vercel.app`

### Via CLI Vercel

```bash
# Installer Vercel CLI
npm i -g vercel

# Se connecter
vercel login

# Déployer
cd frontend
vercel --prod

# Ajouter la variable d'environnement
vercel env add NEXT_PUBLIC_API_URL production
# Entrer l'URL de votre API Render
```

### Troubleshooting Frontend

**Erreur : "Failed to fetch"**
- Vérifier que `NEXT_PUBLIC_API_URL` est bien définie
- Vérifier l'URL (pas de `/` à la fin)
- Redéployer après changement de variable : Dashboard → Deployments → Redeploy

**Les résultats ne s'affichent pas**
- Ouvrir la console du navigateur (F12)
- Vérifier les erreurs réseau
- Vérifier que l'API backend est bien "Live" sur Render

**Erreur CORS**
- Vérifier que le backend a le middleware CORS
- Le fichier `backend/api.py` a déjà la config CORS avec `allow_origins=["*"]`

## 🎯 Étape 3 : Configuration finale

### 1. Tester l'application complète

**Backend** :
```bash
curl https://company-search-api.onrender.com/health
# Doit retourner : {"status":"healthy"}
```

**Frontend** :
- Aller sur votre URL Vercel
- Taper une requête : "PME en Ile-de-France dans la restauration"
- Vérifier que les résultats s'affichent

### 2. Domaine personnalisé (Optionnel)

**Pour le frontend** :
1. Dashboard Vercel → Settings → Domains
2. Ajouter votre domaine (ex: `search.monsite.com`)
3. Configurer les DNS selon les instructions Vercel

**Pour le backend** :
1. Dashboard Render → Settings → Custom Domain
2. Ajouter votre domaine (ex: `api.monsite.com`)
3. Configurer les DNS selon les instructions Render
4. Mettre à jour `NEXT_PUBLIC_API_URL` sur Vercel

### 3. Monitoring

**Render** :
- Dashboard → Logs : Voir les logs en temps réel
- Dashboard → Metrics : CPU, Mémoire, Requêtes

**Vercel** :
- Dashboard → Analytics : Visites, Performance
- Dashboard → Deployments : Historique des déploiements

## 📊 Plans tarifaires

### Render

**Free Plan** :
- ✅ Gratuit
- ⚠️ S'endort après 15 min d'inactivité
- ⚠️ Premier appel après réveil : ~30s
- 750h/mois (suffisant pour 1 service)

**Starter Plan (7$/mois)** :
- ✅ Pas de sleep
- ✅ Meilleure performance
- ✅ 2 services

### Vercel

**Hobby Plan** :
- ✅ Gratuit
- ✅ Bande passante : 100 GB/mois
- ✅ Builds : 6000 min/mois
- ✅ Déploiements illimités

**Pro Plan (20$/mois)** :
- Plus de bande passante
- Analytics avancés
- Support prioritaire

### OpenRouter

**Pay-as-you-go** :
- Modèle `google/gemini-2.5-flash-lite` : ~0.0001$/requête
- Très économique
- Pas de minimum

## 🔐 Checklist de sécurité

- [ ] Clés API stockées dans variables d'environnement
- [ ] Pas de secrets dans le code
- [ ] `.env` dans `.gitignore`
- [ ] HTTPS activé (auto sur Render et Vercel)
- [ ] CORS configuré correctement
- [ ] Logs ne contiennent pas de secrets

## 🚀 Déploiements futurs

### Backend (Render)

**Déploiement automatique** :
- Push sur `main` → Déploiement auto
- Désactiver : Settings → Build & Deploy → Auto-Deploy

**Déploiement manuel** :
- Dashboard → Manual Deploy → Deploy latest commit

### Frontend (Vercel)

**Déploiement automatique** :
- Push sur `main` → Déploiement auto en production
- Push sur autre branche → Preview deployment

**Déploiement manuel** :
- Dashboard → Deployments → Redeploy

## 🎉 C'est terminé !

Votre application est maintenant en production !

**URLs** :
- Backend API : https://company-search-api.onrender.com
- Frontend : https://company-search-frontend.vercel.app
- API Docs : https://company-search-api.onrender.com/docs

## 🆘 Support

En cas de problème :

1. **Vérifier les logs** :
   - Render : Dashboard → Logs
   - Vercel : Dashboard → Deployments → Logs
   - Browser : F12 → Console

2. **Tester l'API directement** :
   ```bash
   curl -X POST https://company-search-api.onrender.com/extract \
     -H "Content-Type: application/json" \
     -d '{"query":"PME en Ile-de-France"}'
   ```

3. **Redéployer** :
   - Parfois un simple redéploiement résout les problèmes

4. **Documentation officielle** :
   - Render : https://render.com/docs
   - Vercel : https://vercel.com/docs
   - Next.js : https://nextjs.org/docs

---

**Bon déploiement ! 🚀**


