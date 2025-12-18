# Guide de Déploiement Render + Vercel

Ce guide explique comment déployer l'application Company Search avec:
- **Backend**: Render (FastAPI + PostgreSQL)
- **Frontend**: Vercel (Next.js)

---

## 🗄️ Étape 1: Créer la Base de Données PostgreSQL sur Render

### 1.1 Créer le Service PostgreSQL

1. Allez sur [Render Dashboard](https://dashboard.render.com/)
2. Cliquez sur **"New +"** → **"PostgreSQL"**
3. Configurez:
   - **Name**: `company-search-db`
   - **Database**: `company_search`
   - **User**: (généré automatiquement)
   - **Region**: `Frankfurt` (ou proche de votre backend)
   - **PostgreSQL Version**: `15` ou `16`
   - **Plan**: **Free** (256MB, suffisant pour Phase 1-2)
4. Cliquez sur **"Create Database"**

### 1.2 Récupérer l'URL de Connexion

Une fois créée, allez dans votre service PostgreSQL et copiez:

- **Internal Database URL** (commence par `postgres://`)

**Format:**
```
postgres://username:password@hostname:5432/database_name
```

**⚠️ Important**: Utilisez **Internal Database URL** (pas External), c'est plus rapide et gratuit.

---

## 🚀 Étape 2: Déployer le Backend sur Render

### 2.1 Créer le Service Web

1. Sur [Render Dashboard](https://dashboard.render.com/)
2. Cliquez sur **"New +"** → **"Web Service"**
3. **Connectez votre dépôt GitHub**:
   - Sélectionnez le repo `company_search`
   - Autorisez Render à accéder au repo

### 2.2 Configuration du Service

**Build & Deploy:**
- **Name**: `company-search-api`
- **Region**: `Frankfurt` (même région que la DB)
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: `Python 3`
- **Build Command**: (déjà défini dans `render.yaml`)
  ```bash
  pip install -r requirements.txt
  alembic upgrade head
  ```
- **Start Command**: (déjà défini dans `render.yaml`)
  ```bash
  uvicorn api:app --host 0.0.0.0 --port $PORT
  ```
- **Plan**: **Free**

### 2.3 Ajouter les Variables d'Environnement

Dans **Environment** → **Environment Variables**, ajoutez:

| Key | Value | Notes |
|-----|-------|-------|
| `PYTHON_VERSION` | `3.11.0` | Version Python |
| `OPENROUTER_API_KEY` | `votre_clé_api` | [Obtenir ici](https://openrouter.ai/keys) |
| `OPENROUTER_MODEL` | `google/gemini-2.5-flash-lite` | Modèle LLM |
| `DATABASE_URL` | `postgres://user:pass@host:5432/db` | Coller l'Internal Database URL (Étape 1.2) |

**⚠️ Crucial**: Pour `DATABASE_URL`, collez **exactement** l'URL copiée depuis votre service PostgreSQL.

### 2.4 Déployer

1. Cliquez sur **"Create Web Service"**
2. Render va:
   - Cloner le repo
   - Installer les dépendances (`pip install`)
   - Exécuter les migrations Alembic (`alembic upgrade head`)
   - Démarrer l'API

**Vérification**:
- Attendez que le build soit "Live" (●)
- Testez l'endpoint: `https://votre-app.onrender.com/health`

**Réponse attendue:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-01-18T12:00:00.000000"
}
```

---

## 🎨 Étape 3: Déployer le Frontend sur Vercel

### 3.1 Créer le Projet Vercel

1. Allez sur [Vercel Dashboard](https://vercel.com/dashboard)
2. Cliquez sur **"Add New..."** → **"Project"**
3. **Importez le repo GitHub**:
   - Sélectionnez `company_search`
   - Autorisez Vercel à accéder

### 3.2 Configuration du Projet

**Framework Preset:** Next.js (détecté automatiquement)

**Build & Output Settings:**
- **Root Directory**: `frontend` (important!)
- **Build Command**: `npm run build` (par défaut)
- **Output Directory**: `.next` (par défaut)
- **Install Command**: `npm install` (par défaut)

### 3.3 Ajouter les Variables d'Environnement

Dans **Environment Variables**, ajoutez:

| Name | Value | Environments |
|------|-------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://company-search-api.onrender.com` | Production, Preview, Development |

**⚠️ Remplacez** `company-search-api` par le nom exact de votre service Render!

**Format complet**:
```
https://[NOM-SERVICE-RENDER].onrender.com
```

**Sans** le trailing slash `/`.

### 3.4 Déployer

1. Cliquez sur **"Deploy"**
2. Vercel va:
   - Installer les dépendances npm
   - Builder l'app Next.js
   - Déployer sur le CDN global

**Vérification**:
- Une fois déployé, visitez l'URL Vercel
- Testez l'extraction directe (existant)
- Testez le chat conversationnel (nouveau)

---

## ✅ Vérification Post-Déploiement

### Backend Health Check

```bash
curl https://votre-app.onrender.com/health
```

**Attendu:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "..."
}
```

### Test Extraction Directe (existant)

```bash
curl -X POST https://votre-app.onrender.com/extract \
  -H "Content-Type: application/json" \
  -d '{"query": "PME restauration en Bretagne"}'
```

**Attendu:** JSON avec critères extraits

### Test Conversation (nouveau)

```bash
curl -X POST https://votre-app.onrender.com/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "Je cherche des PME"}'
```

**Attendu:**
```json
{
  "id": "uuid",
  "status": "active",
  "messages": [
    {"role": "user", "content": "Je cherche des PME", ...},
    {"role": "assistant", "content": "Une PME de quoi exactement ?", ...}
  ]
}
```

---

## 🔧 Dépannage

### Problème: "DATABASE_URL not set"

**Solution:**
1. Vérifiez que `DATABASE_URL` est bien ajoutée dans Render → Environment
2. Redéployez le service (Manual Deploy)

### Problème: "Database connection failed"

**Solution:**
1. Vérifiez que votre service PostgreSQL est "Available"
2. Assurez-vous d'utiliser **Internal Database URL** (pas External)
3. Vérifiez que backend et DB sont dans la **même région**

### Problème: "Alembic migration failed"

**Solution:**
1. Vérifiez les logs de build sur Render
2. Si migration échoue, connectez-vous au Shell Render:
   ```bash
   cd /opt/render/project/src/backend
   alembic upgrade head
   ```

### Problème: Frontend ne se connecte pas au backend

**Solution:**
1. Vérifiez `NEXT_PUBLIC_API_URL` dans Vercel Environment Variables
2. Format correct: `https://nom-service.onrender.com` (sans `/` à la fin)
3. Redéployez le frontend après modification

### Problème: CORS errors

**Solution:**
Le backend autorise déjà tous les origines (`allow_origins=["*"]`). Si CORS persiste:
1. Vérifiez que l'URL API est correcte
2. Testez directement l'API avec curl
3. Vérifiez les logs Render pour des erreurs

### Problème: Render "sleeps" (plan gratuit)

**Comportement normal**:
- Le plan gratuit Render met en veille après 15min d'inactivité
- Premier appel après veille: ~30-60 secondes de démarrage
- Appels suivants: rapides

**Solutions:**
- **Gratuit**: Accepter le cold start
- **Payant**: Passer au plan Starter ($7/mois) pour instance toujours active

---

## 📊 Monitoring

### Logs Backend (Render)

1. Allez sur votre service Render
2. Cliquez sur **"Logs"**
3. Filtrez par niveau: Info, Warning, Error

### Logs Frontend (Vercel)

1. Allez sur votre projet Vercel
2. Cliquez sur **"Deployments"** → dernière déployment → **"View Function Logs"**

### Vérifier Utilisation DB

Render Dashboard → PostgreSQL service → **"Metrics"**:
- Connections
- Storage used (256MB max en free)
- CPU/Memory

---

## 🔄 Mises à Jour

### Backend (Render)

**Auto-deploy activé par défaut**:
1. Poussez sur GitHub (`git push origin main`)
2. Render détecte le changement
3. Re-build et redéploie automatiquement

**Manual deploy**:
- Render Dashboard → Service → **"Manual Deploy"** → **"Clear build cache & deploy"**

### Frontend (Vercel)

**Auto-deploy activé par défaut**:
1. Poussez sur GitHub
2. Vercel détecte et redéploie

**Manual deploy**:
- Vercel Dashboard → Project → **"Deployments"** → **"Redeploy"**

### Migrations Database

**Après modification de models.py**:

1. **Localement** (créer migration):
   ```bash
   cd backend
   alembic revision --autogenerate -m "Description"
   git add alembic/versions/*
   git commit -m "Add migration"
   git push
   ```

2. **Sur Render** (appliquée automatiquement au deploy):
   - Le `buildCommand` dans `render.yaml` exécute `alembic upgrade head`

3. **Ou manuellement via Shell**:
   ```bash
   cd /opt/render/project/src/backend
   alembic upgrade head
   ```

---

## 🎯 Prochaines Étapes

Une fois déployé:

1. ✅ Backend opérationnel avec conversational agent
2. ✅ Frontend connecté au backend
3. 🚧 Phase 3: Améliorer l'UI chat (en cours)
4. 🚧 Phase 4: Optimisations production

---

## 💰 Coûts

### Configuration Actuelle (Gratuite)

| Service | Plan | Coût | Limites |
|---------|------|------|---------|
| Render PostgreSQL | Free | $0 | 256MB, 90 jours retention |
| Render Web Service | Free | $0 | 750h/mois, sleeps après 15min |
| Vercel | Hobby | $0 | 100GB bandwidth, unlimited déploiements |

**Total: $0/mois** ✅

### Upgrade Recommandé (Production)

Si vous dépassez les limites gratuites:

| Service | Plan | Coût | Bénéfices |
|---------|------|------|-----------|
| Render PostgreSQL | Starter | $7/mois | 1GB, backups quotidiens |
| Render Web Service | Starter | $7/mois | Toujours actif, 512MB RAM |
| Vercel | Pro | $20/mois | 1TB bandwidth, analytics |

**Total: ~$34/mois** pour production robuste

---

## 🆘 Support

**Render:**
- [Documentation](https://render.com/docs)
- [Community](https://community.render.com/)

**Vercel:**
- [Documentation](https://vercel.com/docs)
- [Support](https://vercel.com/support)

**Issues Projet:**
- [GitHub Issues](https://github.com/votre-repo/company_search/issues)
