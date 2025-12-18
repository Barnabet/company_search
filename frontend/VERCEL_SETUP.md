# Configuration Vercel - Frontend

## 📝 Résumé

Ce guide explique comment configurer le frontend Next.js sur Vercel pour qu'il communique avec le backend Render.

---

## 🚀 Déploiement Initial

### 1. Importer le Projet

1. Allez sur [Vercel Dashboard](https://vercel.com/dashboard)
2. Cliquez **"Add New..."** → **"Project"**
3. Sélectionnez votre repo GitHub `company_search`
4. Autorisez Vercel

### 2. Configuration du Build

**Framework Preset:** Next.js (détecté automatiquement)

**Root Directory:** `frontend` ⚠️ **IMPORTANT**

**Build & Output Settings:**
- Build Command: `npm run build`
- Output Directory: `.next`
- Install Command: `npm install`

### 3. Variables d'Environnement ⚠️ **CRITIQUE**

Ajoutez cette variable **AVANT** le premier déploiement:

| Name | Value | Environments |
|------|-------|--------------|
| `NEXT_PUBLIC_API_URL` | `https://votre-backend.onrender.com` | Production, Preview, Development |

**⚠️ Remplacez `votre-backend.onrender.com` par l'URL réelle de votre service Render!**

**Format complet:**
```
https://company-search-api-xxx.onrender.com
```

**SANS** le trailing slash `/`

**Cochez:** Production, Preview, Development

### 4. Déployer

Cliquez **"Deploy"**

Vercel va:
- Installer les dépendances (`npm install zustand`)
- Builder l'application Next.js
- Déployer sur le CDN global

**Temps estimé:** 2-3 minutes

---

## ✅ Vérification

### Test 1: Page d'accueil

Visitez votre URL Vercel: `https://votre-app.vercel.app`

**Attendu:**
- Toggle "Mode Conversationnel" / "Extraction Directe" visible
- Mode conversationnel par défaut
- Interface chat s'affiche

### Test 2: Mode Conversationnel

1. Tapez "Je cherche des PME"
2. Cliquez "Envoyer"

**Attendu:**
- Message utilisateur s'affiche
- Agent répond: "Une PME de quoi exactement ? (exemples...)"
- Conversation fluide

### Test 3: Extraction Complète

1. Continuez la conversation: "Dans la restauration en Bretagne"
2. Agent devrait compléter et afficher les résultats

**Attendu:**
- Banner vert "Critères complétés !"
- Résultats d'extraction affichés en dessous

### Test 4: Mode Direct

1. Cliquez sur "⚡ Extraction Directe"
2. Entrez: "PME restauration Bretagne CA > 1M€"
3. Cliquez "🚀 Extraire les critères"

**Attendu:**
- Résultats immédiats sans conversation

---

## 🔧 Dépannage

### Erreur: "Failed to start conversation"

**Cause:** Variable `NEXT_PUBLIC_API_URL` incorrecte ou backend Render down

**Solutions:**
1. Vérifiez l'URL dans Vercel Settings → Environment Variables
2. Testez le backend directement:
   ```bash
   curl https://votre-backend.onrender.com/health
   ```
3. Si backend OK mais frontend KO:
   - Vérifiez les CORS (déjà configurés en `allow_origins=["*"]`)
   - Vérifiez la console browser (F12) pour erreurs

### Erreur: "Module not found: Can't resolve '@/types/conversation'"

**Cause:** Zustand ou types non installés

**Solution:**
1. Vérifiez `package.json` contient `"zustand": "^4.4.7"`
2. Redéployez (Vercel → Deployments → ... → Redeploy)

### Erreur: Build failed

**Cause:** TypeScript errors ou imports manquants

**Solution:**
1. Vérifiez les logs de build sur Vercel
2. Cherchez les lignes `Error:` ou `Type error:`
3. Fix localement puis push

### Mode conversationnel ne fonctionne pas

**Checklist:**
- [ ] Backend Render est "Live" (pas en "Build")
- [ ] `NEXT_PUBLIC_API_URL` correctement définie
- [ ] Backend a `DATABASE_URL` configurée
- [ ] Migrations Alembic exécutées (`alembic upgrade head`)

**Test backend conversations:**
```bash
curl -X POST https://votre-backend.onrender.com/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "PME"}'
```

**Attendu:** JSON avec conversation + messages

---

## 🔄 Mises à Jour

### Après chaque push GitHub

Vercel redéploie automatiquement:
1. Push votre code: `git push origin main`
2. Vercel détecte le changement
3. Build + déploie automatiquement

**Voir le déploiement:**
- Dashboard Vercel → Project → "Deployments"

### Changer l'URL du backend

Si vous changez l'URL Render backend:

1. Vercel Dashboard → Project → **Settings**
2. **Environment Variables**
3. Editez `NEXT_PUBLIC_API_URL`
4. Sauvegardez
5. **Deployments** → ... → **Redeploy**

---

## 📊 Performance

### Premier chargement

**Temps:** ~1-2 secondes (CDN Vercel global)

### Interaction chat

**Latence:** 2-4 secondes par message (dépend du backend Render)

**Optimisations possibles:**
- Backend Render starter plan (toujours actif, pas de cold start)
- Mise en cache Redis pour conversations actives

---

## 💰 Coûts Vercel

### Plan Hobby (Gratuit)

**Limites:**
- 100GB bandwidth/mois
- Déploiements illimités
- Préviews automatiques sur chaque PR

**Suffisant pour:** Développement, démos, petite production

### Plan Pro ($20/mois)

**Bénéfices:**
- 1TB bandwidth
- Analytics
- Support prioritaire

**Nécessaire si:** Traffic élevé, besoin analytics détaillées

---

## 🎨 Customisation

### Changer les couleurs du thème

Editez `tailwind.config.ts`:

```typescript
theme: {
  extend: {
    colors: {
      primary: {
        50: '#...',
        // ...
        600: '#votre-couleur', // Couleur principale
      }
    }
  }
}
```

Redéployez pour voir les changements.

### Ajouter Google Analytics

1. Créez un compte Google Analytics
2. Ajoutez le tracking code dans `app/layout.tsx`
3. Ou utilisez Vercel Analytics (intégré)

---

## 🆘 Support

**Vercel:**
- [Documentation](https://vercel.com/docs)
- [Support](https://vercel.com/support)

**Projet:**
- [GitHub Issues](https://github.com/votre-repo/company_search/issues)

**Backend:**
- Voir [RENDER_DEPLOYMENT.md](../RENDER_DEPLOYMENT.md)
