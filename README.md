# 🔍 Company Search - Agent Conversationnel

Application intelligente pour extraire des critères de recherche d'entreprises françaises via une interface conversationnelle.

## ✨ Fonctionnalités

### 💬 Mode Conversationnel (Nouveau!)
- **Agent intelligent** qui pose des questions de clarification
- **Conversation multi-tours** pour affiner les critères
- **Détection automatique** de complétude (mode MODÉRÉ)
- **Questions contextuelles** avec exemples concrets
- **Fusion automatique** des réponses en requête d'extraction

### ⚡ Mode Extraction Directe (Power Users)
- Extraction immédiate depuis une requête complète
- Idéal pour les utilisateurs avancés

### 📊 Critères Extraits
- **Localisation**: Code postal, département, région, commune
- **Activité**: Secteur d'activité (NAF), libellé
- **Taille**: Tranche d'effectifs, acronyme (TPE/PME/ETI)
- **Critères financiers**: CA, résultat net, rentabilité
- **Critères juridiques**: Catégorie juridique, capital, date création, etc.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  FRONTEND (Next.js 14 + Vercel)         │
│  - React 18 + TypeScript                │
│  - Zustand (state management)           │
│  - Tailwind CSS                          │
│  - Mode Chat + Mode Direct               │
└───────────────┬─────────────────────────┘
                │ HTTPS/JSON
┌───────────────▼─────────────────────────┐
│  BACKEND (FastAPI + Render)             │
│  - Python 3.11                           │
│  - PostgreSQL (conversations)            │
│  - OpenRouter API (Gemini 2.5)           │
│  - SQLAlchemy + Alembic                  │
└─────────────────────────────────────────┘
```

---

## 🚀 Déploiement

### Backend (Render)

**Guide complet:** [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)

**Résumé:**
1. Créer PostgreSQL sur Render (free tier)
2. Créer Web Service (Python)
3. Variables d'environnement:
   - `DATABASE_URL` (Internal Database URL)
   - `OPENROUTER_API_KEY` (depuis https://openrouter.ai/keys)
4. Deploy automatique via `render.yaml`

**URL backend:** `https://company-search-api-xxx.onrender.com`

### Frontend (Vercel)

**Guide complet:** [frontend/VERCEL_SETUP.md](frontend/VERCEL_SETUP.md)

**Résumé:**
1. Importer projet GitHub sur Vercel
2. **Root Directory:** `frontend`
3. Variable d'environnement:
   - `NEXT_PUBLIC_API_URL=https://votre-backend.onrender.com`
4. Deploy automatique

**URL frontend:** `https://company-search.vercel.app`

---

## 🛠️ Développement Local

### Prérequis

- Node.js 18+
- Python 3.11+
- PostgreSQL 15+ (optionnel, pour features conversationnelles)

### Backend

```bash
cd backend

# 1. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Configurer .env
cp .env.example .env
# Editer .env avec vos clés API

# 4. [Optionnel] Setup database
createdb company_search
export DATABASE_URL=postgresql+asyncpg://localhost/company_search
alembic upgrade head

# 5. Lancer l'API
python api.py
# → http://localhost:8000
```

### Frontend

```bash
cd frontend

# 1. Installer dépendances
npm install

# 2. Configurer .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 3. Lancer dev server
npm run dev
# → http://localhost:3000
```

---

## 📖 Utilisation

### Mode Conversationnel

1. Visitez l'application
2. **Mode par défaut:** 💬 Mode Conversationnel
3. Tapez une requête vague: `"Je cherche des PME"`
4. L'agent pose des questions: `"Une PME de quoi exactement ?"`
5. Répondez: `"Dans la restauration"`
6. Continuez jusqu'à complétion des critères
7. Les résultats s'affichent automatiquement

**Exemple de conversation:**
```
User: "Je cherche des PME"
Agent: "Une PME de quoi exactement ? (restauration, informatique...)"
User: "Dans la restauration"
Agent: "J'ai compris : PME dans la restauration. Souhaitez-vous préciser la localisation ?"
User: "En Bretagne"
Agent: "Parfait ! Lancement de la recherche..."
→ Affichage des critères extraits
```

### Mode Direct

1. Cliquez sur **⚡ Extraction Directe**
2. Entrez requête complète: `"PME restauration Bretagne CA > 1M€"`
3. Cliquez **🚀 Extraire les critères**
4. Résultats immédiats

---

## 🧪 Tests

### Backend

```bash
cd backend

# Tester health check
curl http://localhost:8000/health

# Tester extraction directe
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"query": "PME restauration Bretagne"}'

# Tester conversation
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "Je cherche des PME"}'
```

### Frontend

```bash
cd frontend
npm run build  # Vérifier qu'il n'y a pas d'erreurs TypeScript
npm run lint   # Vérifier le linting
```

---

## 📚 Documentation

- **[RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)** - Guide déploiement backend Render
- **[frontend/VERCEL_SETUP.md](frontend/VERCEL_SETUP.md)** - Guide déploiement frontend Vercel
- **[backend/DATABASE_SETUP.md](backend/DATABASE_SETUP.md)** - Guide configuration PostgreSQL
- **[Plan d'implémentation](.claude/plans/spicy-tinkering-church.md)** - Plan technique détaillé

---

## 🏛️ Structure du Projet

```
company_search/
├── backend/
│   ├── api.py                      # FastAPI application
│   ├── database.py                 # SQLAlchemy setup
│   ├── models.py                   # Database models
│   ├── schemas.py                  # Pydantic schemas
│   ├── sector_matcher.py           # Sector normalization
│   ├── services/
│   │   ├── agent_service.py        # AI agent logic
│   │   └── conversation_service.py # CRUD operations
│   ├── routers/
│   │   └── conversation_router.py  # API endpoints
│   ├── alembic/                    # Database migrations
│   ├── data/                       # Reference data (sectors)
│   ├── requirements.txt            # Python dependencies
│   └── render.yaml                 # Render deployment config
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Main page (chat + direct)
│   │   ├── layout.tsx              # Root layout
│   │   └── globals.css             # Global styles + animations
│   ├── components/
│   │   └── Chat/
│   │       ├── ChatInterface.tsx   # Main chat component
│   │       ├── ChatMessage.tsx     # Message bubble
│   │       └── ChatInput.tsx       # User input
│   ├── stores/
│   │   └── conversationStore.ts    # Zustand state management
│   ├── types/
│   │   └── conversation.ts         # TypeScript types
│   ├── package.json                # Dependencies (+ zustand)
│   └── next.config.js              # Next.js config
│
└── README.md                        # Ce fichier
```

---

## 🎯 Fonctionnement de l'Agent

### Analyse de Complétude (Mode MODÉRÉ)

L'agent utilise un système de scoring pour déterminer si la requête est prête:

```python
# Seuils de confiance
≥ 0.9  → Extraction immédiate (ex: "PME restauration Bretagne CA > 1M€")
0.6-0.9 → Confirmation (ex: "PME restauration" → demander localisation?)
< 0.6  → Clarification (ex: "PME" → "PME de quoi?")
```

### Génération de Questions

**Approche hybride:**
1. **Templates** (rapide, déterministe) pour cas courants
2. **LLM** (contextuel) pour cas complexes

**Exemples de templates:**
```python
"missing_activity": "Une PME dans quel secteur ? (restauration, informatique...)"
"missing_location": "Dans quelle région ? (Bretagne, Île-de-France...)"
"vague_activity": "Une PME de quoi exactement ?"
```

### Fusion de Conversation

L'agent combine tous les messages utilisateur en une requête unique:

```
Messages: ["PME", "restauration", "en Bretagne"]
→ Fusion: "PME dans la restauration en Bretagne"
→ Extraction: {activite: {...}, localisation: {...}, taille: {...}}
```

---

## 🔐 Sécurité

- **CORS:** Configuré pour Vercel frontend
- **Environment variables:** Secrets stockés en variables d'environnement
- **API Key:** OpenRouter key protégée (jamais exposée au frontend)
- **Database:** Connection string sécurisée (Internal URL sur Render)
- **Input validation:** Pydantic validation sur toutes les entrées

---

## 💰 Coûts (Gratuit en développement)

| Service | Plan | Coût | Limites |
|---------|------|------|---------|
| **Render PostgreSQL** | Free | $0 | 256MB, 90 jours retention |
| **Render Web Service** | Free | $0 | 750h/mois, sleeps après 15min |
| **Vercel** | Hobby | $0 | 100GB bandwidth |
| **OpenRouter API** | Pay-as-you-go | ~$0.001/requête | Dépend du modèle |

**Total estimé:** < $5/mois pour usage modéré

### Upgrade Production (~$34/mois)

- Render PostgreSQL Starter: $7/mois (1GB, backups)
- Render Web Starter: $7/mois (toujours actif, 512MB)
- Vercel Pro: $20/mois (1TB, analytics)

---

## 🐛 Dépannage

### Backend ne répond pas

```bash
# 1. Vérifier service Render
# Dashboard → Service → "Live" (pas "Sleeping")

# 2. Tester health
curl https://votre-backend.onrender.com/health

# 3. Consulter logs
# Dashboard → Service → "Logs"
```

### Frontend ne se connecte pas au backend

```bash
# 1. Vérifier variable Vercel
# Settings → Environment Variables → NEXT_PUBLIC_API_URL

# 2. Tester backend directement
curl https://votre-backend.onrender.com/

# 3. Vérifier console browser
# F12 → Console → Erreurs CORS ou fetch
```

### Agent ne répond pas

```bash
# 1. Vérifier DATABASE_URL configurée
# Render → Service → Environment

# 2. Tester endpoint conversations
curl -X POST https://votre-backend.onrender.com/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "test"}'

# 3. Vérifier migrations
# Render → Service → Shell → alembic current
```

---

## 📈 Roadmap

### Phase 1 ✅ (Complété)
- [x] Infrastructure database (PostgreSQL + SQLAlchemy)
- [x] Models Conversation & Message
- [x] Migrations Alembic

### Phase 2 ✅ (Complété)
- [x] Agent intelligence (completeness, questions, merge)
- [x] API endpoints conversationnels
- [x] Services CRUD

### Phase 3 ✅ (Complété)
- [x] Frontend chat UI (React components)
- [x] State management (Zustand)
- [x] Mode toggle (chat/direct)

### Phase 4 🚧 (À venir)
- [ ] Cleanup conversations abandonnées (background task)
- [ ] Optimisations database (indexes, pooling)
- [ ] Monitoring et métriques
- [ ] Tests automatisés (pytest + jest)

### Futures Améliorations
- [ ] Authentification utilisateurs
- [ ] Historique de recherches sauvegardées
- [ ] Export résultats (CSV, JSON)
- [ ] Recherche sémantique avec embeddings
- [ ] Support multi-langues
- [ ] Analytics dashboard

---

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📝 License

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---

## 👤 Auteur

Développé avec l'assistance de Claude (Anthropic) - Agent conversationnel intelligent

---

## 🙏 Remerciements

- **OpenRouter** - API LLM
- **Render** - Hosting backend + database
- **Vercel** - Hosting frontend
- **FastAPI** - Framework backend
- **Next.js** - Framework frontend
- **Anthropic Claude** - AI assistant pour le développement

---

## 📧 Support

Pour toute question ou problème:
- 📖 Consultez la [documentation](RENDER_DEPLOYMENT.md)
- 🐛 Ouvrez une [issue GitHub](https://github.com/votre-repo/company_search/issues)
- 💬 Contactez le support Render ou Vercel

---

**Made with ❤️ and 🤖 AI**
