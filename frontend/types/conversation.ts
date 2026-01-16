/**
 * TypeScript types for conversational agent
 */

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  sequence_number: number
  analysis_result?: {
    is_complete: boolean
    missing_fields: string[]
    confidence: number
    suggested_question?: string
    reasoning: string
  }
}

export interface Conversation {
  id: string
  status: 'active' | 'extracting' | 'completed' | 'abandoned'
  created_at: string
  updated_at: string
  completed_at?: string
  messages: Message[]
  extraction_result?: ExtractionResult
}

export interface ExtractionResult {
  localisation: {
    present: boolean
    code_postal: string | null
    departement: string | null
    region: string | null
    commune: string | null
  }
  activite: {
    present: boolean
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

export interface ConversationCreateRequest {
  initial_message: string
}

export interface MessageCreateRequest {
  content: string
}
