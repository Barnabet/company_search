'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import type { ExtractionResult } from '@/types/conversation'
import type { ActivityMatch } from '@/stores/conversationStore'
import {
  MapPin,
  Building2,
  Users,
  TrendingUp,
  Scale,
  Hash,
  CheckCircle2,
  Circle
} from 'lucide-react'

interface SearchFieldsPanelProps {
  extraction: ExtractionResult | null
  companyCount: number | null
  activityMatches: ActivityMatch[] | null
  isLoading: boolean
  isUpdatingSelection: boolean
  onActivitySelect: (index: number) => void
}

// Helper to format financial values
function formatFinancial(value: number | null): string {
  if (value === null) return '-'
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M€`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}k€`
  return `${value}€`
}

// INSEE ranges with their min/max values
const INSEE_RANGES: Record<string, [number, number | null]> = {
  "0 salarie": [0, 0],
  "1 ou 2 salaries": [1, 2],
  "3 a 5 salaries": [3, 5],
  "6 a 9 salaries": [6, 9],
  "10 a 19 salaries": [10, 19],
  "20 a 49 salaries": [20, 49],
  "50 a 99 salaries": [50, 99],
  "100 a 199 salaries": [100, 199],
  "200 a 249 salaries": [200, 249],
  "250 a 499 salaries": [250, 499],
  "500 a 999 salaries": [500, 999],
  "1 000 a 1 999 salaries": [1000, 1999],
  "2 000 a 4 999 salaries": [2000, 4999],
  "5 000 a 9 999 salaries": [5000, 9999],
  "10 000 salaries et plus": [10000, null],
}

// Convert tranches array to simplified range string
function formatSizeRange(tranches: string[]): string {
  if (!tranches || tranches.length === 0) return ''

  let minVal = Infinity
  let maxVal = -Infinity
  let hasUnbounded = false

  for (const tranche of tranches) {
    const range = INSEE_RANGES[tranche]
    if (range) {
      minVal = Math.min(minVal, range[0])
      if (range[1] === null) {
        hasUnbounded = true
      } else {
        maxVal = Math.max(maxVal, range[1])
      }
    }
  }

  if (minVal === Infinity) return tranches.join(', ')

  const formatNum = (n: number) => n.toLocaleString('fr-FR')

  if (hasUnbounded) {
    return `${formatNum(minVal)}+ salariés`
  }
  if (minVal === maxVal) {
    return `${formatNum(minVal)} salariés`
  }
  return `${formatNum(minVal)} - ${formatNum(maxVal)} salariés`
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
  activityMatches,
  isLoading,
  isUpdatingSelection,
  onActivitySelect
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
            <div className="space-y-3">
              {activite?.activite_entreprise && (
                <Badge variant="outline">{activite.activite_entreprise}</Badge>
              )}

              {/* NAF Matches inline */}
              {activityMatches && activityMatches.length > 0 && (
                <TooltipProvider delayDuration={300}>
                  <div className={`space-y-2 ${isUpdatingSelection ? 'opacity-70' : ''}`}>
                    <p className="text-xs text-muted-foreground">
                      Correspondances NAF (cliquez pour modifier)
                    </p>
                    {activityMatches.map((match, index) => (
                      <Tooltip key={index}>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => onActivitySelect(index)}
                            disabled={isUpdatingSelection}
                            className={`w-full text-left p-2 rounded-md border text-sm transition-colors ${
                              match.selected
                                ? 'border-green-500 bg-green-50 dark:bg-green-950'
                                : 'border-transparent bg-muted/30 hover:bg-muted/50'
                            } ${isUpdatingSelection ? 'cursor-wait' : 'cursor-pointer'}`}
                          >
                            <div className="flex items-center gap-2">
                              {match.selected ? (
                                <CheckCircle2 className="h-3.5 w-3.5 text-green-600 shrink-0" />
                              ) : (
                                <Circle className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                              )}
                              <span className={`flex-1 truncate ${match.selected ? 'text-green-700 dark:text-green-300' : ''}`}>
                                {match.activity}
                              </span>
                              <Badge variant="outline" className="text-xs shrink-0">
                                {(match.score * 100).toFixed(0)}%
                              </Badge>
                            </div>
                            {match.naf_codes.length > 0 && (
                              <p className="text-xs text-muted-foreground mt-1 pl-5">
                                {match.naf_codes.join(', ')}
                              </p>
                            )}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="left" className="max-w-xs">
                          <p className="font-medium">{match.activity}</p>
                          {match.naf_codes.length > 0 && (
                            <p className="text-xs text-muted-foreground mt-1">
                              NAF: {match.naf_codes.join(', ')}
                            </p>
                          )}
                        </TooltipContent>
                      </Tooltip>
                    ))}
                  </div>
                </TooltipProvider>
              )}
            </div>
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
                <p className="text-sm">
                  {Array.isArray(taille_entreprise.tranche_effectif)
                    ? formatSizeRange(taille_entreprise.tranche_effectif)
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
