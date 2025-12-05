# 🚀 Guide de Déploiement Vercel

## Étapes rapides

### 1. Préparer le code
```bash
# S'assurer que tout est commité
git add frontend/
git commit -m "Frontend ready for Vercel"
git push origin main
```

### 2. Déployer sur Vercel

#### Via Dashboard (Recommandé)

1. **Aller sur Vercel**
   - https://vercel.com
   - Se connecter avec GitHub

2. **Nouveau Projet**
   - Cliquer sur "Add New..." → "Project"
   - Sélectionner votre repository : `company_search`
   - Cliquer sur "Import"

3. **Configuration du projet**
   
   **Project Settings** :
   - **Project Name** : `company-search-frontend` (ou votre choix)
   - **Framework Preset** : Next.js (détection automatique ✅)
   - **Root Directory** : `frontend` ← **IMPORTANT**
   - **Build Command** : `npm run build` (détection auto)
   - **Output Directory** : `.next` (détection auto)
   - **Install Command** : `npm install` (détection auto)

4. **Variables d'environnement** ⚠️ CRUCIAL
   
   Section "Environment Variables" :
   - Cliquer sur "Add New"
   - **Key** : `NEXT_PUBLIC_API_URL`
   - **Value** : L'URL de votre API Render (ex: `https://company-search-api.onrender.com`)
   - ⚠️ **PAS de `/` à la fin !**
   - **Environments** : Cocher "Production", "Preview", "Development"
   - Cliquer sur "Save"

5. **Déployer**
   - Cliquer sur "Deploy"
   - Attendre 1-3 minutes
   - Une fois "Ready", cliquer sur "Visit"

### 3. Vérifier le déploiement

1. **Tester l'application**
   - Aller sur votre URL Vercel
   - Taper une requête test : "PME en Ile-de-France dans la restauration"
   - Vérifier que les résultats s'affichent

2. **Vérifier les logs si problème**
   - Dashboard → Deployments → Cliquer sur le déploiement
   - Onglet "Logs" pour voir les erreurs

## ⚙️ Configuration détaillée

### Root Directory

**IMPORTANT** : Mettre `frontend` dans Root Directory

Sans ça, Vercel cherchera les fichiers à la racine et ne trouvera pas `package.json`, `app/`, etc.

### Variables d'environnement

**Format** :
```
NEXT_PUBLIC_API_URL=https://votre-api.onrender.com
```

**⚠️ Erreurs communes** :
- ❌ `https://votre-api.onrender.com/` (avec `/` à la fin)
- ✅ `https://votre-api.onrender.com` (sans `/`)

### Build Settings

Vercel détecte automatiquement Next.js, mais vous pouvez vérifier :

- **Framework** : Next.js
- **Build Command** : `npm run build` ou `next build`
- **Output Directory** : `.next` (par défaut)
- **Install Command** : `npm install` ou `npm ci`

## 🔧 Troubleshooting

### Erreur : "Cannot find module"

**Solution** :
- Vérifier que Root Directory = `frontend`
- Vérifier que `package.json` est dans `frontend/`

### Erreur : "Failed to fetch"

**Solution** :
- Vérifier `NEXT_PUBLIC_API_URL` dans les variables d'environnement
- Vérifier que l'URL de l'API est correcte (sans `/` à la fin)
- Vérifier que l'API Render est bien "Live"
- Redéployer après modification des variables

### Erreur : "Build failed"

**Solution** :
- Voir les logs détaillés dans Vercel Dashboard
- Vérifier que toutes les dépendances sont dans `package.json`
- Vérifier que TypeScript compile sans erreur

### L'application se charge mais pas de résultats

**Solution** :
1. Ouvrir la console du navigateur (F12)
2. Vérifier les erreurs réseau
3. Vérifier que `NEXT_PUBLIC_API_URL` est bien définie
4. Tester l'API directement : `https://votre-api.onrender.com/health`

## 📝 Checklist de déploiement

- [ ] Code pushé sur GitHub
- [ ] Root Directory = `frontend`
- [ ] Variable `NEXT_PUBLIC_API_URL` définie
- [ ] URL de l'API sans `/` à la fin
- [ ] API Render est "Live"
- [ ] Build réussi sur Vercel
- [ ] Application accessible
- [ ] Test d'une requête fonctionne

## 🔄 Redéploiement

### Automatique
- Push sur `main` → Déploiement automatique en production
- Push sur autre branche → Preview deployment

### Manuel
- Dashboard → Deployments → Cliquer sur "..." → "Redeploy"

### Après modification des variables d'environnement
- Modifier les variables dans Settings → Environment Variables
- Redéployer manuellement (les variables sont prises en compte au build)

## 🌐 Domaine personnalisé

1. Dashboard → Settings → Domains
2. Ajouter votre domaine (ex: `search.monsite.com`)
3. Configurer les DNS selon les instructions Vercel
4. Attendre la propagation DNS (quelques minutes à quelques heures)

## 📊 Monitoring

- **Analytics** : Dashboard → Analytics (plan Hobby gratuit)
- **Logs** : Dashboard → Deployments → Logs
- **Performance** : Dashboard → Analytics → Web Vitals

## ✅ C'est fait !

Votre frontend est maintenant en ligne sur Vercel !

**URL** : `https://votre-projet.vercel.app`

---

**Besoin d'aide ?** Voir les logs dans Vercel Dashboard ou vérifier la documentation : https://vercel.com/docs

