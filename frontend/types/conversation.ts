/**
 * TypeScript types for extraction results
 */

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
    tranche_effectif: string[] | null
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
