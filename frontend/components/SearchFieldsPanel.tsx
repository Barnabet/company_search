'use client'

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
  Target,
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
  horizontal?: boolean
  fullWidth?: boolean
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
        <Icon className={`h-5 w-5 ${present ? 'text-blue-500' : 'text-muted-foreground'}`} />
        <h3 className="text-sm font-medium">{title}</h3>
        {present && (
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 bg-blue-500/10 text-blue-600 dark:text-blue-400 border-0">
            Actif
          </Badge>
        )}
      </div>
      <div className="pl-7">
        {present ? children : (
          <p className="text-xs text-muted-foreground">Non spécifié</p>
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
  onActivitySelect,
  horizontal = false,
  fullWidth = false
}: SearchFieldsPanelProps) {

  // Loading state
  if (isLoading && !extraction) {
    return (
      <div className={fullWidth ? "p-6 flex gap-6" : horizontal ? "p-4 flex gap-4" : "p-4 space-y-4"}>
        <Skeleton className={fullWidth ? "h-32 w-64 rounded-xl" : horizontal ? "h-20 w-48 rounded-xl" : "h-24 w-full rounded-xl"} />
        <Skeleton className={fullWidth ? "h-32 flex-1 rounded-xl" : horizontal ? "h-20 flex-1 rounded-xl" : "h-64 w-full rounded-xl"} />
      </div>
    )
  }

  // Empty state - shouldn't show in fullWidth mode
  if (!extraction) {
    return (
      <div className={horizontal ? "p-4 flex items-center justify-center" : "p-5"}>
        <div className={horizontal ? "flex items-center gap-4 py-6" : "text-center py-12"}>
          <Target className={horizontal ? "h-6 w-6 text-muted-foreground" : "h-8 w-8 text-muted-foreground mb-4"} />
          <div>
            <h3 className="text-sm font-medium mb-0.5">Critères de recherche</h3>
            <p className="text-xs text-muted-foreground">
              Les critères extraits apparaîtront ici
            </p>
          </div>
        </div>
      </div>
    )
  }

  const { localisation, activite, taille_entreprise, criteres_financiers, criteres_juridiques } = extraction

  const isGoodCount = companyCount !== null && companyCount <= 500

  // Full width layout - NAF on left, criteria on right
  if (fullWidth) {
    return (
      <div className="h-full flex">
        {/* Left: NAF Codes Section - Vertical sidebar */}
        {activityMatches && activityMatches.length > 0 && (
          <div className="w-80 shrink-0 border-r border-border/50 bg-muted/20 p-4 overflow-y-auto">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
              Codes NAF
            </h3>
            <TooltipProvider delayDuration={300}>
              <div className={`space-y-2 ${isUpdatingSelection ? 'opacity-70' : ''}`}>
                {activityMatches.map((match, index) => (
                  <Tooltip key={index}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => onActivitySelect(index)}
                        disabled={isUpdatingSelection}
                        className={`w-full text-left p-3 rounded-xl border transition-all duration-200 ${
                          match.selected
                            ? 'border-blue-500/50 bg-blue-500/10 shadow-sm'
                            : 'border-border/50 bg-background/50 hover:bg-background hover:border-border'
                        } ${isUpdatingSelection ? 'cursor-wait' : 'cursor-pointer'}`}
                      >
                        <div className="flex items-start gap-2">
                          {match.selected ? (
                            <CheckCircle2 className="h-5 w-5 text-blue-500 shrink-0 mt-0.5" />
                          ) : (
                            <Circle className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <p className={`text-sm font-medium truncate ${match.selected ? 'text-blue-700 dark:text-blue-300' : ''}`}>
                                {match.activity}
                              </p>
                              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${
                                match.selected
                                  ? 'bg-blue-500/20 text-blue-700 dark:text-blue-300'
                                  : 'bg-muted text-muted-foreground'
                              }`}>
                                {(match.score * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="text-[10px] text-muted-foreground font-mono">
                              {match.naf_codes.join(', ')}
                            </p>
                          </div>
                        </div>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="max-w-xs">
                      <p className="font-medium text-xs">{match.activity}</p>
                      <p className="text-[10px] text-muted-foreground mt-1 font-mono">
                        NAF: {match.naf_codes.join(', ')}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </TooltipProvider>
          </div>
        )}

        {/* Right: Results count + Criteria */}
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="max-w-4xl mx-auto">
            {/* Results Count Card */}
            {companyCount !== null && (
              <div className={`relative overflow-hidden rounded-2xl p-6 mb-6 ${
                isGoodCount
                  ? 'bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20'
                  : 'bg-gradient-to-br from-amber-500/10 to-orange-500/5 border border-amber-500/20'
              }`}>
                <div className={`absolute -top-12 -right-12 w-32 h-32 rounded-full blur-3xl ${
                  isGoodCount ? 'bg-blue-500/20' : 'bg-amber-500/20'
                }`} />
                <div className="relative flex items-center justify-between">
                  <div>
                    <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Entreprises trouvées
                    </span>
                    <div className={`text-4xl font-bold tracking-tight mt-1 ${
                      isGoodCount
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-amber-600 dark:text-amber-400'
                    }`}>
                      {companyCount.toLocaleString('fr-FR')}
                    </div>
                  </div>
                  {isGoodCount ? (
                    <span className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                      Prêt pour export
                    </span>
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      Affinez vos critères
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Criteria Cards - Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Localisation */}
              <div className={`rounded-xl p-4 border ${localisation?.present ? 'bg-background border-blue-500/20' : 'bg-muted/30 border-border/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <MapPin className={`h-5 w-5 ${localisation?.present ? 'text-blue-500' : 'text-muted-foreground'}`} />
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Localisation</span>
                </div>
                {localisation?.present ? (
                  <p className="text-sm font-medium">{localisation.commune || localisation.departement || localisation.region || localisation.code_postal}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">Non spécifié</p>
                )}
              </div>

              {/* Activite */}
              <div className={`rounded-xl p-4 border ${activite?.present ? 'bg-background border-blue-500/20' : 'bg-muted/30 border-border/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Building2 className={`h-5 w-5 ${activite?.present ? 'text-blue-500' : 'text-muted-foreground'}`} />
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Activité</span>
                </div>
                {activite?.present ? (
                  <p className="text-sm font-medium">{activite.activite_entreprise}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">Non spécifié</p>
                )}
              </div>

              {/* Taille */}
              <div className={`rounded-xl p-4 border ${taille_entreprise?.present ? 'bg-background border-blue-500/20' : 'bg-muted/30 border-border/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Users className={`h-5 w-5 ${taille_entreprise?.present ? 'text-blue-500' : 'text-muted-foreground'}`} />
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Taille</span>
                </div>
                {taille_entreprise?.present ? (
                  <p className="text-sm font-medium">
                    {taille_entreprise.acronyme || (Array.isArray(taille_entreprise.tranche_effectif) ? formatSizeRange(taille_entreprise.tranche_effectif) : taille_entreprise.tranche_effectif)}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">Non spécifié</p>
                )}
              </div>

              {/* Financier */}
              <div className={`rounded-xl p-4 border ${criteres_financiers?.present ? 'bg-background border-blue-500/20' : 'bg-muted/30 border-border/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className={`h-5 w-5 ${criteres_financiers?.present ? 'text-blue-500' : 'text-muted-foreground'}`} />
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Financier</span>
                </div>
                {criteres_financiers?.present ? (
                  <div className="text-sm font-medium space-y-0.5">
                    {criteres_financiers.ca_plus_recent && <p>CA: {formatFinancial(criteres_financiers.ca_plus_recent)}</p>}
                    {criteres_financiers.resultat_net_plus_recent && <p>Résultat: {formatFinancial(criteres_financiers.resultat_net_plus_recent)}</p>}
                    {criteres_financiers.rentabilite_plus_recente && <p>Rentabilité: {criteres_financiers.rentabilite_plus_recente}%</p>}
                    {!criteres_financiers.ca_plus_recent && !criteres_financiers.resultat_net_plus_recent && !criteres_financiers.rentabilite_plus_recente && <p>Défini</p>}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Non spécifié</p>
                )}
              </div>

              {/* Juridique */}
              <div className={`rounded-xl p-4 border ${criteres_juridiques?.present ? 'bg-background border-blue-500/20' : 'bg-muted/30 border-border/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <Scale className={`h-5 w-5 ${criteres_juridiques?.present ? 'text-blue-500' : 'text-muted-foreground'}`} />
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Juridique</span>
                </div>
                {criteres_juridiques?.present ? (
                  <div className="text-sm font-medium space-y-0.5">
                    {criteres_juridiques.categorie_juridique && <p>Forme: {criteres_juridiques.categorie_juridique}</p>}
                    {criteres_juridiques.siege_entreprise && <p>Siège: {criteres_juridiques.siege_entreprise}</p>}
                    {criteres_juridiques.date_creation_entreprise_min && <p>Après: {criteres_juridiques.date_creation_entreprise_min}</p>}
                    {criteres_juridiques.date_creation_entreprise_max && <p>Avant: {criteres_juridiques.date_creation_entreprise_max}</p>}
                    {criteres_juridiques.capital && <p>Capital: {formatFinancial(criteres_juridiques.capital)}</p>}
                    {criteres_juridiques.nombre_etablissements && <p>{criteres_juridiques.nombre_etablissements} établ.</p>}
                    {!criteres_juridiques.categorie_juridique && !criteres_juridiques.siege_entreprise && !criteres_juridiques.date_creation_entreprise_min && !criteres_juridiques.date_creation_entreprise_max && !criteres_juridiques.capital && !criteres_juridiques.nombre_etablissements && <p>Défini</p>}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Non spécifié</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Horizontal layout for stacked design
  if (horizontal) {
    return (
      <div className="p-4">
        <div className="flex gap-4 items-start">
          {/* Company Count - Compact */}
          {companyCount !== null && (
            <div className={`shrink-0 relative overflow-hidden rounded-xl p-4 min-w-[160px] ${
              isGoodCount
                ? 'bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20'
                : 'bg-gradient-to-br from-amber-500/10 to-orange-500/5 border border-amber-500/20'
            }`}>
              <div className="relative">
                <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  Résultats
                </span>
                <div className={`text-2xl font-bold tracking-tight ${
                  isGoodCount
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-amber-600 dark:text-amber-400'
                }`}>
                  {companyCount.toLocaleString('fr-FR')}
                </div>
                {isGoodCount && (
                  <span className="text-[10px] text-blue-600 dark:text-blue-400">
                    Prêt pour export
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Criteria - Horizontal flow */}
          <div className="flex-1 flex flex-wrap gap-3">
            {/* Localisation */}
            {localisation?.present && (
              <div className="bg-background/50 border border-border/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <MapPin className="h-4 w-4 text-blue-500" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase">Localisation</span>
                </div>
                <div className="text-xs font-medium">
                  {localisation.commune || localisation.departement || localisation.region || localisation.code_postal}
                </div>
              </div>
            )}

            {/* Activite */}
            {activite?.present && (
              <div className="bg-background/50 border border-border/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <Building2 className="h-4 w-4 text-blue-500" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase">Activité</span>
                </div>
                <div className="text-xs font-medium">{activite.activite_entreprise}</div>
              </div>
            )}

            {/* Taille */}
            {taille_entreprise?.present && (
              <div className="bg-background/50 border border-border/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <Users className="h-4 w-4 text-blue-500" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase">Taille</span>
                </div>
                <div className="text-xs font-medium">
                  {taille_entreprise.acronyme || (Array.isArray(taille_entreprise.tranche_effectif) ? formatSizeRange(taille_entreprise.tranche_effectif) : taille_entreprise.tranche_effectif)}
                </div>
              </div>
            )}

            {/* Financier */}
            {criteres_financiers?.present && (
              <div className="bg-background/50 border border-border/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <TrendingUp className="h-4 w-4 text-blue-500" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase">Financier</span>
                </div>
                <div className="text-xs font-medium">
                  {criteres_financiers.ca_plus_recent ? `CA: ${formatFinancial(criteres_financiers.ca_plus_recent)}` : ''}
                </div>
              </div>
            )}

            {/* Juridique */}
            {criteres_juridiques?.present && (
              <div className="bg-background/50 border border-border/50 rounded-lg px-3 py-2">
                <div className="flex items-center gap-1.5 mb-1">
                  <Scale className="h-4 w-4 text-blue-500" />
                  <span className="text-[10px] font-medium text-muted-foreground uppercase">Juridique</span>
                </div>
                <div className="text-xs font-medium">
                  {criteres_juridiques.categorie_juridique || criteres_juridiques.siege_entreprise || criteres_juridiques.date_creation_entreprise_min || criteres_juridiques.date_creation_entreprise_max || 'Défini'}
                </div>
              </div>
            )}

            {/* NAF Codes - inline */}
            {activityMatches && activityMatches.length > 0 && (
              <div className="w-full flex flex-wrap gap-1.5 mt-1">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider mr-2">NAF:</span>
                {activityMatches.map((match, index) => (
                  <button
                    key={index}
                    onClick={() => onActivitySelect(index)}
                    disabled={isUpdatingSelection}
                    className={`text-[10px] px-2 py-1 rounded-md transition-all ${
                      match.selected
                        ? 'bg-blue-500/20 text-blue-700 dark:text-blue-300 border border-blue-500/30'
                        : 'bg-muted/50 text-muted-foreground hover:bg-muted border border-transparent'
                    } ${isUpdatingSelection ? 'cursor-wait' : 'cursor-pointer'}`}
                  >
                    {match.selected && <CheckCircle2 className="h-2.5 w-2.5 inline mr-1" />}
                    {match.activity.length > 25 ? match.activity.substring(0, 25) + '...' : match.activity}
                    <span className="ml-1 opacity-60">{(match.score * 100).toFixed(0)}%</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Vertical layout (original)
  return (
    <div className="p-4 space-y-4">
      {/* Company Count Card */}
      {companyCount !== null && (
        <div className={`relative overflow-hidden rounded-xl p-4 ${
          isGoodCount
            ? 'bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20'
            : 'bg-gradient-to-br from-amber-500/10 to-orange-500/5 border border-amber-500/20'
        }`}>
          {/* Decorative glow */}
          <div className={`absolute -top-8 -right-8 w-24 h-24 rounded-full blur-2xl ${
            isGoodCount ? 'bg-blue-500/20' : 'bg-amber-500/20'
          }`} />

          <div className="relative">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Entreprises trouvées
              </span>
              {isGoodCount && (
                <span className="text-[10px] text-blue-600 dark:text-blue-400 font-medium">
                  Prêt pour export
                </span>
              )}
            </div>
            <div className={`text-3xl font-bold tracking-tight ${
              isGoodCount
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-amber-600 dark:text-amber-400'
            }`}>
              {companyCount.toLocaleString('fr-FR')}
            </div>
            {!isGoodCount && (
              <p className="text-[11px] text-muted-foreground mt-2">
                Affinez vos critères pour réduire les résultats
              </p>
            )}
          </div>
        </div>
      )}

      {/* Criteria Sections */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">Critères extraits</h2>

        <div className="rounded-xl border border-border/50 bg-background/50 p-4 space-y-4">
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
                  <div className={`space-y-1.5 ${isUpdatingSelection ? 'opacity-70' : ''}`}>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">
                      Codes NAF correspondants
                    </p>
                    {activityMatches.map((match, index) => (
                      <Tooltip key={index}>
                        <TooltipTrigger asChild>
                          <button
                            onClick={() => onActivitySelect(index)}
                            disabled={isUpdatingSelection}
                            className={`w-full text-left p-2.5 rounded-lg border text-sm transition-all duration-200 ${
                              match.selected
                                ? 'border-blue-500/50 bg-blue-500/10 shadow-sm'
                                : 'border-transparent bg-muted/30 hover:bg-muted/50 hover:border-border/50'
                            } ${isUpdatingSelection ? 'cursor-wait' : 'cursor-pointer'}`}
                          >
                            <div className="flex items-center gap-2">
                              {match.selected ? (
                                <CheckCircle2 className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0" />
                              ) : (
                                <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                              )}
                              <span className={`flex-1 truncate text-xs ${match.selected ? 'text-blue-700 dark:text-blue-300 font-medium' : ''}`}>
                                {match.activity}
                              </span>
                              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                                match.selected
                                  ? 'bg-blue-500/20 text-blue-700 dark:text-blue-300'
                                  : 'bg-muted text-muted-foreground'
                              }`}>
                                {(match.score * 100).toFixed(0)}%
                              </span>
                            </div>
                            {match.naf_codes.length > 0 && (
                              <p className="text-[10px] text-muted-foreground mt-1 pl-5 font-mono">
                                {match.naf_codes.join(', ')}
                              </p>
                            )}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent side="left" className="max-w-xs">
                          <p className="font-medium text-xs">{match.activity}</p>
                          {match.naf_codes.length > 0 && (
                            <p className="text-[10px] text-muted-foreground mt-1 font-mono">
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
              <CriteriaField
                label="Rentabilité"
                value={criteres_financiers?.rentabilite_plus_recente
                  ? `${criteres_financiers.rentabilite_plus_recente}%`
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
              <CriteriaField label="Créées après" value={criteres_juridiques?.date_creation_entreprise_min} />
              <CriteriaField label="Créées avant" value={criteres_juridiques?.date_creation_entreprise_max} />
              <CriteriaField
                label="Capital min."
                value={criteres_juridiques?.capital
                  ? formatFinancial(criteres_juridiques.capital)
                  : null
                }
              />
              <CriteriaField
                label="Établissements"
                value={criteres_juridiques?.nombre_etablissements
                  ? String(criteres_juridiques.nombre_etablissements)
                  : null
                }
              />
            </div>
          </CriteriaSection>
        </div>
      </div>
    </div>
  )
}
