'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import type { ExtractionResult } from '@/types/conversation'
import {
  MapPin,
  Building2,
  Users,
  TrendingUp,
  Scale,
  Hash
} from 'lucide-react'

interface SearchFieldsPanelProps {
  extraction: ExtractionResult | null
  companyCount: number | null
  isLoading: boolean
}

// Helper to format financial values
function formatFinancial(value: number | null): string {
  if (value === null) return '-'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M€`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}k€`
  return `${value}€`
}

// Section component for each criteria group
function CriteriaSection({
  title,
  icon: Icon,
  present,
  children
}: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  present: boolean
  children: React.ReactNode
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">{title}</h3>
        {present && (
          <Badge variant="secondary" className="text-xs">
            Défini
          </Badge>
        )}
      </div>
      <div className="pl-6">
        {present ? children : (
          <p className="text-sm text-muted-foreground italic">Non spécifié</p>
        )}
      </div>
    </div>
  )
}

function CriteriaField({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export default function SearchFieldsPanel({
  extraction,
  companyCount,
  isLoading
}: SearchFieldsPanelProps) {

  // Loading state
  if (isLoading && !extraction) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  // Empty state
  if (!extraction) {
    return (
      <div className="p-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Critères de recherche</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Décrivez votre recherche dans le chat pour voir les critères extraits ici.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const { localisation, activite, taille_entreprise, criteres_financiers, criteres_juridiques } = extraction

  return (
    <div className="p-4 space-y-4">
      {/* Company Count Card */}
      {companyCount !== null && (
        <Card className={companyCount <= 500 ? 'border-green-500 bg-green-50 dark:bg-green-950' : 'border-orange-500 bg-orange-50 dark:bg-orange-950'}>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Hash className="h-5 w-5" />
                <span className="text-sm font-medium">Résultats</span>
              </div>
              <span className={`text-2xl font-bold ${
                companyCount <= 500 ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400'
              }`}>
                {companyCount.toLocaleString('fr-FR')}
              </span>
            </div>
            {companyCount > 500 && (
              <p className="text-xs text-muted-foreground mt-2">
                Affinez vos critères pour réduire le nombre de résultats
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Criteria Sections */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Critères extraits</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Localisation */}
          <CriteriaSection
            title="Localisation"
            icon={MapPin}
            present={localisation?.present ?? false}
          >
            <div className="space-y-1">
              <CriteriaField label="Région" value={localisation?.region} />
              <CriteriaField label="Département" value={localisation?.departement} />
              <CriteriaField label="Commune" value={localisation?.commune} />
              <CriteriaField label="Code postal" value={localisation?.code_postal} />
            </div>
          </CriteriaSection>

          <Separator />

          {/* Activite */}
          <CriteriaSection
            title="Activité"
            icon={Building2}
            present={activite?.present ?? false}
          >
            {activite?.activite_entreprise && (
              <Badge variant="outline">{activite.activite_entreprise}</Badge>
            )}
          </CriteriaSection>

          <Separator />

          {/* Taille */}
          <CriteriaSection
            title="Taille"
            icon={Users}
            present={taille_entreprise?.present ?? false}
          >
            <div className="space-y-1">
              {taille_entreprise?.acronyme && (
                <Badge>{taille_entreprise.acronyme}</Badge>
              )}
              {taille_entreprise?.tranche_effectif && (
                <p className="text-xs text-muted-foreground mt-1">
                  {Array.isArray(taille_entreprise.tranche_effectif)
                    ? taille_entreprise.tranche_effectif.join(', ')
                    : taille_entreprise.tranche_effectif
                  }
                </p>
              )}
            </div>
          </CriteriaSection>

          <Separator />

          {/* Financier */}
          <CriteriaSection
            title="Critères financiers"
            icon={TrendingUp}
            present={criteres_financiers?.present ?? false}
          >
            <div className="space-y-1">
              <CriteriaField
                label="CA minimum"
                value={criteres_financiers?.ca_plus_recent
                  ? formatFinancial(criteres_financiers.ca_plus_recent)
                  : null
                }
              />
              <CriteriaField
                label="Résultat net"
                value={criteres_financiers?.resultat_net_plus_recent
                  ? formatFinancial(criteres_financiers.resultat_net_plus_recent)
                  : null
                }
              />
            </div>
          </CriteriaSection>

          <Separator />

          {/* Juridique */}
          <CriteriaSection
            title="Critères juridiques"
            icon={Scale}
            present={criteres_juridiques?.present ?? false}
          >
            <div className="space-y-1">
              <CriteriaField label="Catégorie" value={criteres_juridiques?.categorie_juridique} />
              <CriteriaField label="Siège" value={criteres_juridiques?.siege_entreprise} />
              <CriteriaField label="Date création" value={criteres_juridiques?.date_creation_entreprise} />
            </div>
          </CriteriaSection>
        </CardContent>
      </Card>
    </div>
  )
}
