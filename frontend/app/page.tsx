'use client'

import { useState } from 'react'

interface ExtractionResult {
  localisation: {
    present: boolean
    code_postal: string | null
    departement: string | null
    region: string | null
    commune: string | null
  }
  activite: {
    present: boolean
    libelle_secteur: string | null
    activite_entreprise: string | null
  }
  taille_entreprise: {
    present: boolean
    tranche_effectif: string | null
    acronyme: string | null
  }
  criteres_financiers: {
    present: boolean
    ca_plus_recent: number | null
    resultat_net_plus_recent: number | null
    rentabilite_plus_recente: number | null
  }
  criteres_juridiques: {
    present: boolean
    categorie_juridique: string | null
    siege_entreprise: string | null
    date_creation_entreprise: string | null
    capital: number | null
    date_changement_dirigeant: string | null
    nombre_etablissements: number | null
  }
}

const EXAMPLE_QUERIES = [
  "Je cherche des PME en Ile-de-France dans la restauration avec un CA supérieur à 1M€",
  "Trouver des entreprises créées après 2020 dans le secteur informatique",
  "Entreprises de construction dans les Hauts-de-Seine avec plus de 50 salariés",
  "Sociétés commerciales en Bretagne spécialisées en conseil de gestion"
]

export default function Home() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ExtractionResult | null>(null)

  // URL de l'API - à remplacer par votre URL Render après déploiement
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!query.trim()) {
      setError('Veuillez saisir une requête')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Erreur lors de l\'extraction')
      }

      const data = await response.json()
      setResult(data.result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Une erreur est survenue')
    } finally {
      setLoading(false)
    }
  }

  const formatValue = (value: any): string => {
    if (value === null) return 'Non spécifié'
    if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
    if (typeof value === 'number') {
      if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M€`
      if (value >= 1000) return `${(value / 1000).toFixed(0)}k€`
      return value.toString()
    }
    return value
  }

  const ResultSection = ({ title, data, present }: { title: string, data: any, present: boolean }) => {
    if (!present) {
      return (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">{title}</h3>
          <p className="text-gray-500 dark:text-gray-400 italic">Aucun critère spécifié</p>
        </div>
      )
    }

    const fields = Object.entries(data).filter(([key]) => key !== 'present')

    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-primary-200 dark:border-primary-800 shadow-sm">
        <h3 className="text-lg font-semibold mb-3 text-primary-700 dark:text-primary-400">{title}</h3>
        <dl className="space-y-2">
          {fields.map(([key, value]) => (
            <div key={key} className="flex justify-between items-start">
              <dt className="text-sm font-medium text-gray-600 dark:text-gray-400 capitalize">
                {key.replace(/_/g, ' ')}:
              </dt>
              <dd className="text-sm text-gray-900 dark:text-white font-semibold ml-4 text-right">
                {formatValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-gray-900 dark:to-gray-800 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            🔍 Company Search
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300">
            Extraction intelligente de critères de recherche d'entreprises
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Décrivez votre recherche en langage naturel, nous extrayons les critères structurés
          </p>
        </div>

        {/* Search Form */}
        <div className="mb-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="query" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Votre requête
              </label>
              <textarea
                id="query"
                rows={4}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-800 dark:text-white"
                placeholder="Ex: Je cherche des PME en Ile-de-France dans la restauration avec un CA supérieur à 1M€"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 px-6 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Extraction en cours...
                </span>
              ) : (
                '🚀 Extraire les critères'
              )}
            </button>
          </form>

          {/* Example Queries */}
          <div className="mt-4">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Essayez ces exemples :</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((example, index) => (
                <button
                  key={index}
                  onClick={() => setQuery(example)}
                  className="text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded-full transition-colors"
                >
                  {example.substring(0, 50)}...
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-8 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-center">
              <span className="text-2xl mr-3">⚠️</span>
              <div>
                <h3 className="text-red-800 dark:text-red-300 font-semibold">Erreur</h3>
                <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-6">
            <div className="bg-gradient-to-r from-primary-500 to-primary-600 rounded-lg p-6 text-white shadow-lg">
              <h2 className="text-2xl font-bold mb-2">✅ Critères extraits avec succès !</h2>
              <p className="text-primary-100">Voici l'analyse structurée de votre requête :</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <ResultSection
                title="📍 Localisation"
                data={result.localisation}
                present={result.localisation.present}
              />
              <ResultSection
                title="💼 Activité"
                data={result.activite}
                present={result.activite.present}
              />
              <ResultSection
                title="👥 Taille d'entreprise"
                data={result.taille_entreprise}
                present={result.taille_entreprise.present}
              />
              <ResultSection
                title="💰 Critères financiers"
                data={result.criteres_financiers}
                present={result.criteres_financiers.present}
              />
              <ResultSection
                title="⚖️ Critères juridiques"
                data={result.criteres_juridiques}
                present={result.criteres_juridiques.present}
              />
            </div>

            {/* Raw JSON */}
            <details className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
              <summary className="cursor-pointer text-sm font-semibold text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400">
                🔧 Voir le JSON brut
              </summary>
              <pre className="mt-4 p-4 bg-gray-900 text-green-400 rounded text-xs overflow-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>Powered by OpenRouter AI • Built with Next.js & FastAPI</p>
        </div>
      </div>
    </main>
  )
}

