'use client'

import { useState } from 'react'
import ChatInterface from '@/components/Chat/ChatInterface'
import type { ExtractionResult } from '@/types/conversation'

const EXAMPLE_QUERIES = [
  "PME dans la restauration en Ile-de-France",
  "Entreprises informatiques créées après 2020",
  "Sociétés de construction avec plus de 50 salariés",
  "ETI en Bretagne spécialisées en conseil"
]

export default function Home() {
  const [mode, setMode] = useState<'chat' | 'direct'>('chat')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ExtractionResult | null>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://company-search-v248.onrender.com'

  const handleDirectExtract = async (e: React.FormEvent) => {
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
        headers: { 'Content-Type': 'application/json' },
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
    if (value === null) return '-'
    if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
    if (typeof value === 'number') {
      if (value >= 1000000) return `${(value / 1000000).toFixed(1)} M€`
      if (value >= 1000) return `${(value / 1000).toFixed(0)} k€`
      return value.toString()
    }
    return value
  }

  const ResultSection = ({ title, data, present }: { title: string, data: any, present: boolean }) => {
    if (!present) {
      return (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{title}</h3>
          <p className="text-gray-400 dark:text-gray-500 text-sm mt-2">Non spécifié</p>
        </div>
      )
    }

    const fields = Object.entries(data).filter(([key, value]) => key !== 'present' && value !== null)

    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
        <h3 className="text-sm font-semibold text-blue-600 dark:text-blue-400 uppercase tracking-wide mb-3">{title}</h3>
        <dl className="space-y-2">
          {fields.map(([key, value]) => (
            <div key={key} className="flex justify-between items-center">
              <dt className="text-sm text-gray-600 dark:text-gray-400">
                {key.replace(/_/g, ' ')}
              </dt>
              <dd className="text-sm font-medium text-gray-900 dark:text-white">
                {formatValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Company Search
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Recherche d'entreprises par critères
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex mb-6 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setMode('chat')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mode === 'chat'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Mode conversationnel
          </button>
          <button
            onClick={() => setMode('direct')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              mode === 'direct'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Extraction directe
          </button>
        </div>

        {/* Content */}
        {mode === 'chat' ? (
          <ChatInterface onExtractionComplete={(extractionResult) => setResult(extractionResult)} />
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <form onSubmit={handleDirectExtract} className="space-y-4">
              <div>
                <label htmlFor="query" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Requête
                </label>
                <textarea
                  id="query"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white text-sm"
                  placeholder="Ex: PME informatique en Ile-de-France"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={loading}
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50"
              >
                {loading ? 'Extraction...' : 'Extraire les critères'}
              </button>
            </form>

            {/* Examples */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Exemples :</p>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_QUERIES.map((example, index) => (
                  <button
                    key={index}
                    onClick={() => setQuery(example)}
                    className="text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 px-2 py-1 rounded transition-colors"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="mt-6 space-y-4">
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <p className="text-green-700 dark:text-green-400 font-medium text-sm">Critères extraits</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ResultSection
                title="Localisation"
                data={result.localisation || {}}
                present={result.localisation?.present ?? false}
              />
              <ResultSection
                title="Activité"
                data={result.activite || {}}
                present={result.activite?.present ?? false}
              />
              <ResultSection
                title="Taille"
                data={result.taille_entreprise || {}}
                present={result.taille_entreprise?.present ?? false}
              />
              <ResultSection
                title="Financier"
                data={result.criteres_financiers || {}}
                present={result.criteres_financiers?.present ?? false}
              />
              <ResultSection
                title="Juridique"
                data={result.criteres_juridiques || {}}
                present={result.criteres_juridiques?.present ?? false}
              />
            </div>

            {/* Raw JSON */}
            <details className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4">
              <summary className="cursor-pointer text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900">
                Voir le JSON
              </summary>
              <pre className="mt-3 p-3 bg-gray-900 text-green-400 rounded text-xs overflow-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </main>
  )
}
