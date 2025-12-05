# Company Search Frontend

Interface web moderne pour l'extraction de critères de recherche d'entreprises françaises.

## 🚀 Déploiement sur Vercel

### Méthode rapide (Recommandée)

1. **Push votre code sur GitHub**

2. **Importer sur Vercel**
   - Aller sur [Vercel](https://vercel.com)
   - Cliquer sur "New Project"
   - Importer votre repository GitHub
   - Vercel détectera automatiquement Next.js

3. **Configuration**
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js (détection automatique)
   - **Build Command**: `npm run build` (par défaut)
   - **Output Directory**: `.next` (par défaut)

4. **Variables d'environnement**
   - Ajouter `NEXT_PUBLIC_API_URL` avec l'URL de votre API Render
   - Exemple: `https://company-search-api.onrender.com`
   - ⚠️ **IMPORTANT**: Pas de `/` à la fin de l'URL !

5. **Déployer**
   - Cliquer sur "Deploy"
   - Votre app sera disponible sur `https://votre-app.vercel.app`

## 🔧 Développement local

### Prérequis
- Node.js 18+ 
- npm ou yarn

### Installation

1. Installer les dépendances :
```bash
cd frontend
npm install
```

2. Créer un fichier `.env.local` :
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Lancer le serveur de développement :
```bash
npm run dev
```

4. Ouvrir [http://localhost:3000](http://localhost:3000)

## 📦 Structure

```
frontend/
├── app/
│   ├── layout.tsx        # Layout principal
│   ├── page.tsx          # Page d'accueil avec le formulaire
│   └── globals.css       # Styles globaux
├── public/               # Assets statiques
├── package.json          # Dépendances
├── tsconfig.json         # Configuration TypeScript
├── tailwind.config.ts    # Configuration Tailwind CSS
├── next.config.js       # Configuration Next.js
└── README.md            # Ce fichier
```

## 🎨 Fonctionnalités

- ✅ Interface moderne et responsive
- ✅ Thème clair/sombre automatique
- ✅ Exemples de requêtes cliquables
- ✅ Affichage structuré des résultats
- ✅ Visualisation du JSON brut
- ✅ Gestion des erreurs
- ✅ Loading states
- ✅ TypeScript pour la sécurité des types

## 🔗 Configuration de l'API

L'application utilise la variable d'environnement `NEXT_PUBLIC_API_URL` pour se connecter à l'API backend.

**Important**: Les variables commençant par `NEXT_PUBLIC_` sont exposées au client et doivent être configurées au moment du build.

### Sur Vercel

1. Aller dans les paramètres du projet
2. Section "Environment Variables"
3. Ajouter `NEXT_PUBLIC_API_URL` avec l'URL de votre API Render
4. Redéployer l'application

## 🎯 Utilisation

1. Saisir une requête en langage naturel dans le champ de texte
2. Cliquer sur "Extraire les critères" ou appuyer sur Entrée
3. Les critères sont extraits et affichés de manière structurée :
   - 📍 Localisation (région, département, code postal, commune)
   - 💼 Activité (secteur, code NAF)
   - 👥 Taille d'entreprise (effectifs, acronyme)
   - 💰 Critères financiers (CA, résultat net, rentabilité)
   - ⚖️ Critères juridiques (forme juridique, capital, dates)

## 🛠️ Build de production

```bash
npm run build
npm start
```

## 🌐 Domaine personnalisé sur Vercel

1. Aller dans les paramètres du projet sur Vercel
2. Section "Domains"
3. Ajouter votre domaine personnalisé
4. Suivre les instructions pour configurer les DNS

## 🔒 Sécurité

- Ne jamais commit les fichiers `.env.local`
- Toujours utiliser `NEXT_PUBLIC_` pour les variables exposées au client
- Activer HTTPS en production (automatique sur Vercel)

## 🐛 Debug

Pour voir les logs de build sur Vercel :
1. Aller dans l'onglet "Deployments"
2. Cliquer sur le déploiement
3. Voir les logs détaillés

## 📝 License

MIT

